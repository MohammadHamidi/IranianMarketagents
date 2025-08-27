#!/usr/bin/env python3
"""
Price History Tracking System
Tracks price changes over time and provides analytics for Iranian e-commerce
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    """Represents a price point in time"""
    timestamp: str
    price_toman: int
    price_usd: float
    vendor: str
    availability: bool
    url: str = ""

@dataclass
class PriceHistory:
    """Complete price history for a product"""
    product_id: str
    title: str
    category: str
    price_points: List[PricePoint]
    first_seen: str
    last_updated: str
    price_trend: str  # 'increasing', 'decreasing', 'stable'
    volatility_score: float
    min_price: int
    max_price: int
    average_price: float
    price_change_30d: float
    price_change_7d: float

@dataclass
class PriceAlert:
    """Price alert configuration and trigger"""
    alert_id: str
    product_id: str
    alert_type: str  # 'price_drop', 'price_increase', 'availability_change'
    threshold: float
    current_value: float
    trigger_value: float
    is_active: bool
    created_at: str
    last_triggered: Optional[str] = None

class PriceHistoryTracker:
    """
    Tracks and analyzes price history for Iranian e-commerce products
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.history_retention_days = 90  # Keep 90 days of history

    async def record_price_point(self, product_data: Dict) -> bool:
        """
        Record a new price point for a product
        """
        try:
            product_id = product_data['product_id']

            # Create price point
            price_point = PricePoint(
                timestamp=datetime.now(timezone.utc).isoformat(),
                price_toman=product_data['price_toman'],
                price_usd=product_data['price_usd'],
                vendor=product_data['vendor'],
                availability=product_data['availability'],
                url=product_data.get('product_url', '')
            )

            # Store in Redis list (most recent first)
            history_key = f"price_history:{product_id}"
            price_data = json.dumps(asdict(price_point))

            # Add to history (keep only recent entries)
            await self.redis_client.lpush(history_key, price_data)

            # Trim to keep only last 90 days worth of data (assuming 3 records per day)
            await self.redis_client.ltrim(history_key, 0, 270)

            # Update product metadata
            metadata_key = f"product_metadata:{product_id}"
            metadata = {
                'product_id': product_id,
                'title': product_data['title'],
                'category': product_data['category'],
                'last_price': product_data['price_toman'],
                'last_update': price_point.timestamp,
                'vendor': product_data['vendor']
            }

            await self.redis_client.hset(metadata_key, mapping=metadata)
            await self.redis_client.expire(metadata_key, 86400 * 30)  # 30 days

            # Update global price statistics
            await self._update_global_stats(product_data)

            logger.info(f"💰 Recorded price point for {product_id}: {product_data['price_toman']:,} تومان")
            return True

        except Exception as e:
            logger.error(f"❌ Error recording price point: {e}")
            return False

    async def get_price_history(self, product_id: str, days: int = 30) -> Optional[PriceHistory]:
        """
        Get complete price history for a product
        """
        try:
            history_key = f"price_history:{product_id}"
            metadata_key = f"product_metadata:{product_id}"

            # Get metadata
            metadata = await self.redis_client.hgetall(metadata_key)
            if not metadata:
                return None

            # Get price points
            price_data = await self.redis_client.lrange(history_key, 0, -1)
            if not price_data:
                return None

            # Parse price points
            price_points = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            for data in price_data:
                try:
                    point_data = json.loads(data.decode())
                    point_timestamp = datetime.fromisoformat(point_data['timestamp'].replace('Z', '+00:00'))

                    if point_timestamp >= cutoff_date:
                        price_points.append(PricePoint(**point_data))
                except:
                    continue

            if not price_points:
                return None

            # Sort by timestamp (oldest first)
            price_points.sort(key=lambda x: x.timestamp)

            # Calculate statistics
            prices = [p.price_toman for p in price_points]
            min_price = min(prices)
            max_price = max(prices)
            average_price = sum(prices) / len(prices)

            # Calculate price changes
            price_change_30d = self._calculate_price_change(price_points, 30)
            price_change_7d = self._calculate_price_change(price_points, 7)

            # Determine trend
            price_trend = self._determine_price_trend(price_points)

            # Calculate volatility
            volatility_score = self._calculate_volatility(price_points)

            return PriceHistory(
                product_id=product_id,
                title=metadata.get(b'title', b'').decode(),
                category=metadata.get(b'category', b'').decode(),
                price_points=price_points,
                first_seen=price_points[0].timestamp if price_points else datetime.now(timezone.utc).isoformat(),
                last_updated=price_points[-1].timestamp if price_points else datetime.now(timezone.utc).isoformat(),
                price_trend=price_trend,
                volatility_score=round(volatility_score, 2),
                min_price=min_price,
                max_price=max_price,
                average_price=round(average_price, 2),
                price_change_30d=round(price_change_30d, 2),
                price_change_7d=round(price_change_7d, 2)
            )

        except Exception as e:
            logger.error(f"❌ Error getting price history: {e}")
            return None

    async def analyze_price_trends(self, category: str = None, days: int = 30) -> Dict:
        """
        Analyze price trends across products/categories
        """
        try:
            # Get all products in category
            product_keys = await self.redis_client.keys("product:*")
            category_products = []

            for key in product_keys:
                metadata_key = f"product_metadata:{key.split(':')[1]}"
                metadata = await self.redis_client.hgetall(metadata_key)

                if metadata:
                    product_category = metadata.get(b'category', b'').decode()
                    if not category or product_category == category:
                        category_products.append(metadata.get(b'product_id', b'').decode())

            # Analyze trends for each product
            trend_analysis = {
                'category': category or 'all',
                'total_products': len(category_products),
                'analyzed_products': 0,
                'trending_up': 0,
                'trending_down': 0,
                'stable': 0,
                'high_volatility': 0,
                'price_changes': [],
                'top_gainers': [],
                'top_losers': []
            }

            for product_id in category_products[:50]:  # Limit for performance
                history = await self.get_price_history(product_id, days)
                if history:
                    trend_analysis['analyzed_products'] += 1

                    # Count trends
                    if history.price_trend == 'increasing':
                        trend_analysis['trending_up'] += 1
                    elif history.price_trend == 'decreasing':
                        trend_analysis['trending_down'] += 1
                    else:
                        trend_analysis['stable'] += 1

                    # Count high volatility
                    if history.volatility_score > 10:
                        trend_analysis['high_volatility'] += 1

                    # Track price changes
                    if abs(history.price_change_7d) > 5:
                        trend_analysis['price_changes'].append({
                            'product_id': product_id,
                            'title': history.title,
                            'change_7d': history.price_change_7d,
                            'current_price': history.price_points[-1].price_toman if history.price_points else 0
                        })

            # Sort price changes
            trend_analysis['price_changes'].sort(key=lambda x: x['change_7d'], reverse=True)
            trend_analysis['top_gainers'] = trend_analysis['price_changes'][:5]
            trend_analysis['top_losers'] = trend_analysis['price_changes'][-5:][::-1]

            return trend_analysis

        except Exception as e:
            logger.error(f"❌ Error analyzing price trends: {e}")
            return {}

    async def create_price_alert(self, product_id: str, alert_type: str, threshold: float) -> bool:
        """
        Create a price alert for a product
        """
        try:
            alert_id = f"alert_{product_id}_{int(asyncio.get_event_loop().time())}"

            # Get current price
            metadata_key = f"product_metadata:{product_id}"
            metadata = await self.redis_client.hgetall(metadata_key)

            if not metadata:
                logger.warning(f"⚠️ Product {product_id} not found for alert creation")
                return False

            current_price = int(metadata.get(b'last_price', b'0').decode())

            alert = PriceAlert(
                alert_id=alert_id,
                product_id=product_id,
                alert_type=alert_type,
                threshold=threshold,
                current_value=current_price,
                trigger_value=current_price,  # Will be updated when triggered
                is_active=1,  # Convert boolean to int for Redis
                created_at=datetime.now(timezone.utc).isoformat()
            )

            # Store alert
            alert_key = f"price_alert:{alert_id}"
            await self.redis_client.hset(alert_key, mapping=asdict(alert))
            await self.redis_client.expire(alert_key, 86400 * 30)  # 30 days

            # Add to product alerts list
            alerts_list_key = f"product_alerts:{product_id}"
            await self.redis_client.sadd(alerts_list_key, alert_id)
            await self.redis_client.expire(alerts_list_key, 86400 * 30)

            logger.info(f"🔔 Created price alert {alert_id} for {product_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error creating price alert: {e}")
            return False

    async def check_price_alerts(self) -> List[Dict]:
        """
        Check all active price alerts and return triggered ones
        """
        try:
            triggered_alerts = []

            # Get all alert keys
            alert_keys = await self.redis_client.keys("price_alert:*")

            for key in alert_keys:
                alert_data = await self.redis_client.hgetall(key)
                if not alert_data:
                    continue

                alert = PriceAlert(**{k.decode(): v.decode() for k, v in alert_data.items()})

                if not alert.is_active:
                    continue

                # Get current price
                metadata_key = f"product_metadata:{alert.product_id}"
                metadata = await self.redis_client.hgetall(metadata_key)

                if not metadata:
                    continue

                current_price = int(metadata.get(b'last_price', b'0').decode())

                # Check if alert should trigger
                should_trigger = False

                if alert.alert_type == 'price_drop' and current_price <= alert.threshold:
                    should_trigger = True
                elif alert.alert_type == 'price_increase' and current_price >= alert.threshold:
                    should_trigger = True

                if should_trigger:
                    # Update alert
                    alert.trigger_value = current_price
                    alert.last_triggered = datetime.now(timezone.utc).isoformat()
                    alert.is_active = False  # One-time alert

                    await self.redis_client.hset(key, mapping=asdict(alert))

                    # Add to triggered alerts
                    triggered_alerts.append({
                        'alert_id': alert.alert_id,
                        'product_id': alert.product_id,
                        'alert_type': alert.alert_type,
                        'threshold': alert.threshold,
                        'trigger_value': alert.trigger_value,
                        'previous_value': alert.current_value,
                        'triggered_at': alert.last_triggered
                    })

            return triggered_alerts

        except Exception as e:
            logger.error(f"❌ Error checking price alerts: {e}")
            return []

    def _calculate_price_change(self, price_points: List[PricePoint], days: int) -> float:
        """Calculate price change over specified days"""
        if len(price_points) < 2:
            return 0.0

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_prices = [p for p in price_points if datetime.fromisoformat(p.timestamp.replace('Z', '+00:00')) >= cutoff_date]

        if len(recent_prices) < 2:
            return 0.0

        old_price = recent_prices[0].price_toman
        new_price = recent_prices[-1].price_toman

        if old_price == 0:
            return 0.0

        return ((new_price - old_price) / old_price) * 100

    def _determine_price_trend(self, price_points: List[PricePoint]) -> str:
        """Determine price trend from price points"""
        if len(price_points) < 3:
            return "stable"

        # Calculate trend using simple linear regression slope
        n = len(price_points)
        if n < 3:
            return "stable"

        # Use last 10 points for trend analysis
        recent_points = price_points[-10:]

        x = list(range(len(recent_points)))
        y = [p.price_toman for p in recent_points]

        # Simple slope calculation
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)

        if slope > 100:  # Increasing significantly
            return "increasing"
        elif slope < -100:  # Decreasing significantly
            return "decreasing"
        else:
            return "stable"

    def _calculate_volatility(self, price_points: List[PricePoint]) -> float:
        """Calculate price volatility score"""
        if len(price_points) < 2:
            return 0.0

        prices = [p.price_toman for p in price_points]
        if len(prices) < 2:
            return 0.0

        # Calculate coefficient of variation
        mean_price = sum(prices) / len(prices)
        if mean_price == 0:
            return 0.0

        variance = sum((price - mean_price) ** 2 for price in prices) / len(prices)
        std_dev = variance ** 0.5
        volatility = (std_dev / mean_price) * 100

        return volatility

    async def _update_global_stats(self, product_data: Dict):
        """Update global price statistics"""
        try:
            stats_key = "global_price_stats"
            category = product_data['category']

            # Get current stats
            current_stats = await self.redis_client.hgetall(stats_key) or {}

            # Update category stats
            category_key = f"{category}_count"
            category_avg_key = f"{category}_avg_price"

            current_count = int(current_stats.get(category_key.encode(), b'0').decode() or 0)
            current_avg = float(current_stats.get(category_avg_key.encode(), b'0').decode() or 0)

            # Calculate new average
            new_count = current_count + 1
            new_avg = ((current_avg * current_count) + product_data['price_toman']) / new_count

            # Update stats
            await self.redis_client.hset(stats_key, category_key, str(new_count))
            await self.redis_client.hset(stats_key, category_avg_key, str(round(new_avg, 2)))

            # Update last update timestamp
            await self.redis_client.hset(stats_key, "last_updated", datetime.now(timezone.utc).isoformat())

        except Exception as e:
            logger.warning(f"⚠️ Error updating global stats: {e}")
