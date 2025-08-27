#!/usr/bin/env python3
"""
Intelligent Alert System for Iranian Price Intelligence
Provides notifications for price drops, increases, and market opportunities
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

from services.scraper.price_history_tracker import PriceHistoryTracker, PriceAlert
from services.search_service import SearXNGSearchService

logger = logging.getLogger(__name__)

@dataclass
class AlertNotification:
    """Alert notification data"""
    notification_id: str
    alert_id: str
    product_id: str
    product_title: str
    alert_type: str
    message: str
    old_price: int
    new_price: int
    price_change_percent: float
    vendor: str
    product_url: str
    timestamp: str
    sent_via: List[str]  # ['email', 'webhook', 'slack']

class AlertSystem:
    """
    Intelligent alert system that monitors price changes and market opportunities
    """

    def __init__(self, redis_client=None, smtp_config: Dict = None):
        self.redis_client = redis_client
        self.price_tracker = PriceHistoryTracker(redis_client)
        self.search_service = SearXNGSearchService()

        # SMTP configuration for email alerts
        self.smtp_config = smtp_config or {
            'server': 'smtp.gmail.com',
            'port': 587,
            'username': '',
            'password': '',
            'from_email': 'alerts@iranianprice.local'
        }

        # Alert thresholds
        self.alert_thresholds = {
            'price_drop_percent': 5.0,  # Alert on 5%+ price drops
            'price_increase_percent': 10.0,  # Alert on 10%+ price increases
            'high_volatility_threshold': 15.0,  # Alert on high volatility
            'market_opportunity_threshold': 20.0  # Price difference between vendors
        }

        # Notification channels
        self.notification_channels = []

    def add_notification_channel(self, channel_type: str, config: Dict):
        """
        Add a notification channel (email, webhook, slack, etc.)
        """
        self.notification_channels.append({
            'type': channel_type,
            'config': config
        })

    async def run_alert_checks(self) -> List[AlertNotification]:
        """
        Run all alert checks and return triggered notifications
        """
        logger.info("🔍 Running alert checks...")

        notifications = []

        try:
            # Check price change alerts
            price_notifications = await self._check_price_change_alerts()
            notifications.extend(price_notifications)

            # Check market opportunity alerts
            market_notifications = await self._check_market_opportunity_alerts()
            notifications.extend(market_notifications)

            # Check volatility alerts
            volatility_notifications = await self._check_volatility_alerts()
            notifications.extend(volatility_notifications)

            # Check availability alerts
            availability_notifications = await self._check_availability_alerts()
            notifications.extend(availability_notifications)

            # Send notifications
            await self._send_notifications(notifications)

            logger.info(f"🔔 Generated {len(notifications)} alert notifications")
            return notifications

        except Exception as e:
            logger.error(f"❌ Error running alert checks: {e}")
            return []

    async def _check_price_change_alerts(self) -> List[AlertNotification]:
        """Check for price change alerts"""
        notifications = []

        try:
            # Check existing user-defined alerts
            triggered_alerts = await self.price_tracker.check_price_alerts()

            for alert in triggered_alerts:
                # Get product details
                product_details = await self._get_product_details(alert['product_id'])
                if not product_details:
                    continue

                notification = AlertNotification(
                    notification_id=f"notif_{alert['alert_id']}_{int(asyncio.get_event_loop().time())}",
                    alert_id=alert['alert_id'],
                    product_id=alert['product_id'],
                    product_title=product_details['title'],
                    alert_type=alert['alert_type'],
                    message=self._generate_price_alert_message(alert, product_details),
                    old_price=alert.get('previous_value', 0),
                    new_price=alert.get('trigger_value', 0),
                    price_change_percent=((alert.get('trigger_value', 0) - alert.get('previous_value', 0)) / alert.get('previous_value', 1)) * 100,
                    vendor=product_details['vendor'],
                    product_url=product_details['product_url'],
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    sent_via=[]
                )
                notifications.append(notification)

            # Check for automatic price drop/increase alerts
            auto_notifications = await self._check_automatic_price_alerts()
            notifications.extend(auto_notifications)

            return notifications

        except Exception as e:
            logger.error(f"❌ Error checking price change alerts: {e}")
            return []

    async def _check_market_opportunity_alerts(self) -> List[AlertNotification]:
        """Check for market opportunity alerts (significant price differences)"""
        notifications = []

        try:
            # Get price gaps analysis
            if hasattr(self.price_tracker, 'redis_client') and self.price_tracker.redis_client:
                # Use the existing price gap discovery from AI agents
                product_keys = await self.redis_client.keys("product:*")

                # Group products by title
                product_groups = {}
                for key in product_keys[:100]:  # Limit for performance
                    product_data = await self.redis_client.hgetall(key)
                    if not product_data:
                        continue

                    title = product_data.get(b'title', b'').decode()
                    price = int(product_data.get(b'price_toman', b'0').decode())
                    vendor = product_data.get(b'vendor', b'').decode()
                    product_id = product_data.get(b'product_id', b'').decode()
                    product_url = product_data.get(b'product_url', b'').decode()

                    if title not in product_groups:
                        product_groups[title] = []
                    product_groups[title].append({
                        'price': price,
                        'vendor': vendor,
                        'product_id': product_id,
                        'url': product_url
                    })

                # Find significant price gaps
                for title, vendors in product_groups.items():
                    if len(vendors) > 1:
                        prices = [v['price'] for v in vendors]
                        min_price = min(prices)
                        max_price = max(prices)
                        difference_percent = ((max_price - min_price) / min_price) * 100

                        if difference_percent >= self.alert_thresholds['market_opportunity_threshold']:
                            # Find cheapest and most expensive
                            cheapest = min(vendors, key=lambda x: x['price'])
                            expensive = max(vendors, key=lambda x: x['price'])

                            notification = AlertNotification(
                                notification_id=f"market_opp_{int(asyncio.get_event_loop().time())}_{hash(title) % 10000}",
                                alert_id="market_opportunity",
                                product_id=cheapest['product_id'],
                                product_title=title,
                                alert_type="market_opportunity",
                                message=f"💰 Market Opportunity: {difference_percent:.1f}% price difference for '{title}' - Buy from {cheapest['vendor']} for {cheapest['price']:,} تومان instead of {expensive['vendor']} for {expensive['price']:,} تومان",
                                old_price=expensive['price'],
                                new_price=cheapest['price'],
                                price_change_percent=-difference_percent,
                                vendor=cheapest['vendor'],
                                product_url=cheapest['url'],
                                timestamp=datetime.now(timezone.utc).isoformat(),
                                sent_via=[]
                            )
                            notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"❌ Error checking market opportunity alerts: {e}")
            return []

    async def _check_volatility_alerts(self) -> List[AlertNotification]:
        """Check for high volatility products"""
        notifications = []

        try:
            # Get recent products and check their volatility
            product_keys = await self.redis_client.keys("product_metadata:*")

            for key in product_keys[:50]:  # Limit for performance
                metadata = await self.redis_client.hgetall(key)
                if not metadata:
                    continue

                product_id = metadata.get(b'product_id', b'').decode()

                # Get price history
                history = await self.price_tracker.get_price_history(product_id, days=7)
                if history and history.volatility_score > self.alert_thresholds['high_volatility_threshold']:
                    notification = AlertNotification(
                        notification_id=f"volatility_{product_id}_{int(asyncio.get_event_loop().time())}",
                        alert_id="high_volatility",
                        product_id=product_id,
                        product_title=history.title,
                        alert_type="high_volatility",
                        message=f"⚡ High Volatility Alert: '{history.title}' has {history.volatility_score:.1f}% volatility - Monitor closely",
                        old_price=history.min_price,
                        new_price=history.max_price,
                        price_change_percent=history.price_change_7d,
                        vendor=metadata.get(b'vendor', b'').decode(),
                        product_url="",  # Could be added from metadata
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sent_via=[]
                    )
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"❌ Error checking volatility alerts: {e}")
            return []

    async def _check_availability_alerts(self) -> List[AlertNotification]:
        """Check for availability changes (back in stock, out of stock)"""
        notifications = []

        try:
            # This would require tracking availability history
            # For now, return empty list as this needs more infrastructure
            return notifications

        except Exception as e:
            logger.error(f"❌ Error checking availability alerts: {e}")
            return []

    async def _check_automatic_price_alerts(self) -> List[AlertNotification]:
        """Check for automatic price alerts based on thresholds"""
        notifications = []

        try:
            # Get products with significant recent price changes
            product_keys = await self.redis_client.keys("product:*")

            for key in product_keys[:100]:  # Limit for performance
                product_data = await self.redis_client.hgetall(key)
                if not product_data:
                    continue

                product_id = product_data.get(b'product_id', b'').decode()

                # Get price history for last 24 hours
                history = await self.price_tracker.get_price_history(product_id, days=1)
                if not history or len(history.price_points) < 2:
                    continue

                # Check for significant price changes
                recent_change = history.price_change_7d

                if abs(recent_change) >= self.alert_thresholds['price_drop_percent']:
                    alert_type = "price_drop" if recent_change < 0 else "price_increase"

                    notification = AlertNotification(
                        notification_id=f"auto_{alert_type}_{product_id}_{int(asyncio.get_event_loop().time())}",
                        alert_id="automatic",
                        product_id=product_id,
                        product_title=history.title,
                        alert_type=alert_type,
                        message=f"📈 Price {alert_type.replace('_', ' ')}: '{history.title}' changed by {recent_change:.1f}%",
                        old_price=int((history.price_points[-1].price_toman * 100) / (100 + recent_change)),
                        new_price=history.price_points[-1].price_toman,
                        price_change_percent=recent_change,
                        vendor=history.price_points[-1].vendor,
                        product_url=history.price_points[-1].url,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        sent_via=[]
                    )
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"❌ Error checking automatic price alerts: {e}")
            return []

    async def _send_notifications(self, notifications: List[AlertNotification]):
        """Send notifications through configured channels"""
        for notification in notifications:
            sent_channels = []

            for channel in self.notification_channels:
                try:
                    if channel['type'] == 'email':
                        await self._send_email_notification(notification, channel['config'])
                        sent_channels.append('email')
                    elif channel['type'] == 'webhook':
                        await self._send_webhook_notification(notification, channel['config'])
                        sent_channels.append('webhook')
                    elif channel['type'] == 'slack':
                        await self._send_slack_notification(notification, channel['config'])
                        sent_channels.append('slack')
                except Exception as e:
                    logger.error(f"❌ Failed to send {channel['type']} notification: {e}")

            notification.sent_via = sent_channels

            # Store notification in Redis
            if self.redis_client:
                notif_key = f"notification:{notification.notification_id}"
                await self.redis_client.hset(notif_key, mapping=asdict(notification))
                await self.redis_client.expire(notif_key, 86400 * 7)  # Keep for 7 days

    async def _send_email_notification(self, notification: AlertNotification, config: Dict):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from_email']
            msg['To'] = config['to_email']
            msg['Subject'] = f"Iranian Price Alert: {notification.product_title}"

            body = f"""
            Iranian Price Intelligence Alert

            Product: {notification.product_title}
            Alert Type: {notification.alert_type}
            Vendor: {notification.vendor}

            {notification.message}

            Price Change: {notification.price_change_percent:.1f}%
            Old Price: {notification.old_price:,} تومان
            New Price: {notification.new_price:,} تومان

            Product URL: {notification.product_url}

            Timestamp: {notification.timestamp}

            --
            Iranian Price Intelligence System
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
            server.starttls()
            server.login(self.smtp_config['username'], self.smtp_config['password'])
            text = msg.as_string()
            server.sendmail(self.smtp_config['from_email'], config['to_email'], text)
            server.quit()

            logger.info(f"📧 Email sent to {config['to_email']} for {notification.product_title}")

        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            raise

    async def _send_webhook_notification(self, notification: AlertNotification, config: Dict):
        """Send webhook notification"""
        try:
            import aiohttp

            webhook_data = {
                'alert_type': notification.alert_type,
                'product_title': notification.product_title,
                'message': notification.message,
                'price_change_percent': notification.price_change_percent,
                'old_price': notification.old_price,
                'new_price': notification.new_price,
                'vendor': notification.vendor,
                'product_url': notification.product_url,
                'timestamp': notification.timestamp
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(config['url'], json=webhook_data) as response:
                    if response.status not in [200, 201, 202]:
                        raise Exception(f"Webhook failed with status {response.status}")

            logger.info(f"🔗 Webhook sent to {config['url']} for {notification.product_title}")

        except Exception as e:
            logger.error(f"❌ Failed to send webhook: {e}")
            raise

    async def _send_slack_notification(self, notification: AlertNotification, config: Dict):
        """Send Slack notification"""
        try:
            import aiohttp

            slack_message = {
                'channel': config['channel'],
                'text': f"🚨 Iranian Price Alert: {notification.product_title}",
                'attachments': [{
                    'color': 'warning' if 'drop' in notification.alert_type else 'good',
                    'fields': [
                        {'title': 'Alert Type', 'value': notification.alert_type, 'short': True},
                        {'title': 'Vendor', 'value': notification.vendor, 'short': True},
                        {'title': 'Price Change', 'value': f"{notification.price_change_percent:.1f}%", 'short': True},
                        {'title': 'New Price', 'value': f"{notification.new_price:,} تومان", 'short': True},
                        {'title': 'Message', 'value': notification.message, 'short': False}
                    ]
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(config['webhook_url'], json=slack_message) as response:
                    if response.status not in [200, 201, 202]:
                        raise Exception(f"Slack webhook failed with status {response.status}")

            logger.info(f"💬 Slack notification sent for {notification.product_title}")

        except Exception as e:
            logger.error(f"❌ Failed to send Slack notification: {e}")
            raise

    async def _get_product_details(self, product_id: str) -> Optional[Dict]:
        """Get product details from Redis"""
        try:
            metadata_key = f"product_metadata:{product_id}"
            metadata = await self.redis_client.hgetall(metadata_key)

            if metadata:
                return {
                    'title': metadata.get(b'title', b'').decode(),
                    'vendor': metadata.get(b'vendor', b'').decode(),
                    'product_url': metadata.get(b'product_url', b'').decode()
                }

            # Fallback to product data
            product_key = f"product:{product_id}"
            product_data = await self.redis_client.hgetall(product_key)

            if product_data:
                return {
                    'title': product_data.get(b'title', b'').decode(),
                    'vendor': product_data.get(b'vendor', b'').decode(),
                    'product_url': product_data.get(b'product_url', b'').decode()
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error getting product details: {e}")
            return None

    def _generate_price_alert_message(self, alert: Dict, product_details: Dict) -> str:
        """Generate human-readable alert message"""
        alert_type = alert['alert_type']
        threshold = alert.get('threshold', 0)
        trigger_value = alert.get('trigger_value', 0)

        if alert_type == 'price_drop':
            return f"📉 Price dropped below {threshold:,} تومان! Now {trigger_value:,} تومان on {product_details['vendor']}"
        elif alert_type == 'price_increase':
            return f"📈 Price increased above {threshold:,} تومان! Now {trigger_value:,} تومان on {product_details['vendor']}"
        else:
            return f"⚠️ Price alert triggered: {alert_type} at {trigger_value:,} تومان"

    async def create_smart_alert(self, product_id: str, alert_type: str = "auto") -> bool:
        """
        Create a smart alert that automatically sets thresholds based on product history
        """
        try:
            # Get price history
            history = await self.price_tracker.get_price_history(product_id, days=30)
            if not history:
                logger.warning(f"⚠️ No price history available for smart alert on {product_id}")
                return False

            current_price = history.price_points[-1].price_toman if history.price_points else 0

            if alert_type == "auto":
                # Create both drop and increase alerts based on volatility
                volatility = history.volatility_score

                # Price drop alert: 5% drop or based on volatility
                drop_threshold = max(current_price * 0.95, current_price - (volatility * 10000))

                # Price increase alert: 10% increase or significant jump
                increase_threshold = min(current_price * 1.10, current_price + (volatility * 20000))

                # Create alerts
                await self.price_tracker.create_price_alert(product_id, "price_drop", drop_threshold)
                await self.price_tracker.create_price_alert(product_id, "price_increase", increase_threshold)

            elif alert_type == "price_drop":
                # Smart price drop: alert if drops 5% or more
                threshold = current_price * 0.95
                await self.price_tracker.create_price_alert(product_id, "price_drop", threshold)

            elif alert_type == "volatility":
                # Alert on high volatility
                threshold = history.volatility_score + 5
                await self.price_tracker.create_price_alert(product_id, "high_volatility", threshold)

            logger.info(f"🔔 Created smart alert for {product_id} ({alert_type})")
            return True

        except Exception as e:
            logger.error(f"❌ Error creating smart alert: {e}")
            return False
