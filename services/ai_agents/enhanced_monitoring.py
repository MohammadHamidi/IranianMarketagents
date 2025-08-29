#!/usr/bin/env python3
"""
Enhanced Monitoring and Logging System
Comprehensive monitoring, alerting, and performance tracking
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import redis.asyncio as redis
import psutil
import aiofiles
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

@dataclass
class MetricPoint:
    """Individual metric measurement"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str]

@dataclass
class Alert:
    """System alert"""
    alert_id: str
    severity: str  # "info", "warning", "error", "critical"
    title: str
    message: str
    timestamp: float
    source: str
    resolved: bool = False
    resolved_at: Optional[float] = None

class EnhancedMonitoringSystem:
    """Comprehensive monitoring system with alerting and analytics"""

    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client

        # Metrics storage
        self.metrics_buffer = deque(maxlen=10000)
        self.active_alerts = {}
        self.alert_callbacks = []

        # System health tracking
        self.system_health = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "network_io": [],
            "redis_connection": True,
            "last_health_check": 0
        }

        # Performance baselines
        self.baselines = {
            "scraping_success_rate": {"min": 0.5, "max": 1.0, "avg": 0.7},
            "response_time": {"min": 0, "max": 30, "avg": 5},
            "cache_hit_ratio": {"min": 0.3, "max": 1.0, "avg": 0.7},
            "error_rate": {"min": 0, "max": 0.1, "avg": 0.05}
        }

        # Alert thresholds
        self.alert_thresholds = {
            "scraping_success_rate": 0.3,
            "response_time": 20,
            "error_rate": 0.15,
            "memory_usage": 85,  # percentage
            "cpu_usage": 90,     # percentage
            "disk_usage": 90     # percentage
        }

        # Log file path
        self.log_dir = Path("logs/monitoring")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize monitoring system"""
        if not self.redis:
            self.redis = redis.from_url('redis://localhost:6379/0')

        # Start background monitoring tasks
        asyncio.create_task(self._health_check_loop())
        asyncio.create_task(self._metrics_flush_loop())
        asyncio.create_task(self._alert_check_loop())

        logger.info("✅ Enhanced monitoring system initialized")

    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    async def record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric measurement"""
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )

        self.metrics_buffer.append(metric)

        # Check for threshold violations
        await self._check_metric_thresholds(metric)

    async def record_scraping_result(self, domain: str, success: bool, duration: float,
                                   products_found: int, tool_used: str, errors: List[str]):
        """Record scraping operation result"""
        tags = {
            "domain": domain,
            "tool": tool_used,
            "success": str(success)
        }

        await self.record_metric("scraping_duration", duration, tags)
        await self.record_metric("products_found", products_found, tags)
        await self.record_metric("scraping_success", 1 if success else 0, tags)
        await self.record_metric("error_count", len(errors), tags)

        # Log scraping result
        await self._log_scraping_event(domain, success, duration, products_found, tool_used, errors)

    async def record_api_request(self, endpoint: str, method: str, duration: float,
                               status_code: int, user_agent: str = ""):
        """Record API request metrics"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }

        await self.record_metric("api_request_duration", duration, tags)
        await self.record_metric("api_request_count", 1, tags)

        # Log slow requests
        if duration > 5.0:  # Log requests taking more than 5 seconds
            await self._log_slow_request(endpoint, method, duration, status_code)

    async def record_error(self, error_type: str, message: str, stack_trace: str = "",
                          context: Dict[str, Any] = None):
        """Record error occurrence"""
        tags = {"error_type": error_type}
        if context:
            tags.update({k: str(v) for k, v in context.items()})

        await self.record_metric("error_count", 1, tags)

        # Create alert for critical errors
        if error_type in ["critical", "selenium_error", "connection_error"]:
            await self._create_alert(
                severity="error",
                title=f"{error_type.replace('_', ' ').title()}",
                message=message,
                source="error_handler"
            )

        # Log error details
        await self._log_error(error_type, message, stack_trace, context)

    async def _check_metric_thresholds(self, metric: MetricPoint):
        """Check if metric violates alert thresholds"""
        threshold_key = None

        if metric.name == "scraping_success" and metric.value < self.alert_thresholds["scraping_success_rate"]:
            threshold_key = "scraping_success_rate"
        elif metric.name == "api_request_duration" and metric.value > self.alert_thresholds["response_time"]:
            threshold_key = "response_time"
        elif metric.name == "error_count" and metric.value > self.alert_thresholds["error_rate"]:
            threshold_key = "error_rate"

        if threshold_key:
            await self._create_alert(
                severity="warning",
                title=f"Threshold Violation: {metric.name}",
                message=f"Metric {metric.name} value {metric.value} violates threshold",
                source="threshold_monitor"
            )

    async def _create_alert(self, severity: str, title: str, message: str, source: str):
        """Create and dispatch alert"""
        alert = Alert(
            alert_id=f"alert_{int(time.time())}_{hash(title) % 1000}",
            severity=severity,
            title=title,
            message=message,
            timestamp=time.time(),
            source=source
        )

        # Store alert
        self.active_alerts[alert.alert_id] = alert

        # Dispatch to callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

        # Auto-resolve certain alerts after timeout
        if severity in ["info", "warning"]:
            asyncio.create_task(self._auto_resolve_alert(alert.alert_id, 300))  # 5 minutes

        logger.warning(f"🚨 Alert [{severity}]: {title} - {message}")

    async def _auto_resolve_alert(self, alert_id: str, delay_seconds: int):
        """Auto-resolve alert after delay"""
        await asyncio.sleep(delay_seconds)

        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()

            logger.info(f"✅ Alert auto-resolved: {alert.title}")

    async def resolve_alert(self, alert_id: str):
        """Manually resolve alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = time.time()
            logger.info(f"✅ Alert manually resolved: {alert.title}")

    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await self._perform_health_check()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)

    async def _perform_health_check(self):
        """Perform comprehensive system health check"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_health["cpu_usage"].append(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.system_health["memory_usage"].append(memory_percent)

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            self.system_health["disk_usage"].append(disk_percent)

            # Network I/O
            network = psutil.net_io_counters()
            self.system_health["network_io"].append({
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv
            })

            # Redis connection
            try:
                await self.redis.ping()
                self.system_health["redis_connection"] = True
            except Exception:
                self.system_health["redis_connection"] = False

            self.system_health["last_health_check"] = time.time()

            # Check for health alerts
            if cpu_percent > self.alert_thresholds["cpu_usage"]:
                await self._create_alert(
                    "warning", "High CPU Usage",
                    ".1f",
                    "health_monitor"
                )

            if memory_percent > self.alert_thresholds["memory_usage"]:
                await self._create_alert(
                    "warning", "High Memory Usage",
                    ".1f",
                    "health_monitor"
                )

            if disk_percent > self.alert_thresholds["disk_usage"]:
                await self._create_alert(
                    "warning", "High Disk Usage",
                    ".1f",
                    "health_monitor"
                )

            if not self.system_health["redis_connection"]:
                await self._create_alert(
                    "error", "Redis Connection Failed",
                    "Unable to connect to Redis database",
                    "health_monitor"
                )

        except Exception as e:
            logger.error(f"Error performing health check: {e}")

    async def _metrics_flush_loop(self):
        """Background metrics flush loop"""
        while True:
            try:
                await self._flush_metrics_to_storage()
                await asyncio.sleep(300)  # Flush every 5 minutes
            except Exception as e:
                logger.error(f"Error in metrics flush loop: {e}")
                await asyncio.sleep(300)

    async def _flush_metrics_to_storage(self):
        """Flush buffered metrics to persistent storage"""
        if not self.metrics_buffer:
            return

        try:
            # Group metrics by name and time window
            metrics_by_name = defaultdict(list)
            for metric in self.metrics_buffer:
                metrics_by_name[metric.name].append(metric)

            # Calculate aggregations
            aggregated_metrics = {}
            for name, metrics in metrics_by_name.items():
                values = [m.value for m in metrics]
                aggregated_metrics[name] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "timestamp": time.time()
                }

            # Store in Redis
            for name, data in aggregated_metrics.items():
                key = f"metrics:{name}:{int(time.time() // 300) * 300}"  # 5-minute windows
                await self.redis.setex(key, 86400, json.dumps(data))  # 24 hour TTL

            # Clear buffer
            self.metrics_buffer.clear()

            logger.info(f"📊 Flushed {len(aggregated_metrics)} metric types to storage")

        except Exception as e:
            logger.error(f"Error flushing metrics: {e}")

    async def _alert_check_loop(self):
        """Background alert check loop"""
        while True:
            try:
                await self._check_alert_conditions()
                await asyncio.sleep(120)  # Check every 2 minutes
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(120)

    async def _check_alert_conditions(self):
        """Check for alert conditions based on recent metrics"""
        try:
            # Check scraping success rate over last hour
            success_rate = await self._calculate_success_rate_last_hour()
            if success_rate < self.alert_thresholds["scraping_success_rate"]:
                await self._create_alert(
                    "warning", "Low Scraping Success Rate",
                    ".2%",
                    "alert_monitor"
                )

            # Check error rate
            error_rate = await self._calculate_error_rate_last_hour()
            if error_rate > self.alert_thresholds["error_rate"]:
                await self._create_alert(
                    "error", "High Error Rate",
                    ".2%",
                    "alert_monitor"
                )

        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")

    async def _calculate_success_rate_last_hour(self) -> float:
        """Calculate scraping success rate over last hour"""
        try:
            # Get metrics from Redis
            pattern = "metrics:scraping_success:*"
            keys = await self.redis.keys(pattern)

            total_attempts = 0
            successful_attempts = 0

            for key in keys:
                data = await self.redis.get(key)
                if data:
                    metrics = json.loads(data)
                    total_attempts += metrics.get("count", 0)
                    successful_attempts += metrics.get("sum", 0)

            return successful_attempts / max(1, total_attempts)

        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 1.0  # Default to 100% if calculation fails

    async def _calculate_error_rate_last_hour(self) -> float:
        """Calculate error rate over last hour"""
        try:
            pattern = "metrics:error_count:*"
            keys = await self.redis.keys(pattern)

            total_errors = 0
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    metrics = json.loads(data)
                    total_errors += metrics.get("sum", 0)

            # Estimate total operations (rough approximation)
            return min(1.0, total_errors / max(1, total_errors * 10))

        except Exception as e:
            logger.error(f"Error calculating error rate: {e}")
            return 0.0

    async def _log_scraping_event(self, domain: str, success: bool, duration: float,
                                 products_found: int, tool_used: str, errors: List[str]):
        """Log scraping event to file"""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "scraping_result",
                "domain": domain,
                "success": success,
                "duration": duration,
                "products_found": products_found,
                "tool_used": tool_used,
                "errors": errors,
                "error_count": len(errors)
            }

            await self._write_log_entry("scraping.log", log_entry)

        except Exception as e:
            logger.error(f"Error logging scraping event: {e}")

    async def _log_slow_request(self, endpoint: str, method: str, duration: float, status_code: int):
        """Log slow API request"""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "slow_request",
                "endpoint": endpoint,
                "method": method,
                "duration": duration,
                "status_code": status_code
            }

            await self._write_log_entry("slow_requests.log", log_entry)

        except Exception as e:
            logger.error(f"Error logging slow request: {e}")

    async def _log_error(self, error_type: str, message: str, stack_trace: str = "",
                        context: Dict[str, Any] = None):
        """Log error details"""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "error",
                "error_type": error_type,
                "message": message,
                "stack_trace": stack_trace,
                "context": context or {}
            }

            await self._write_log_entry("errors.log", log_entry)

        except Exception as e:
            logger.error(f"Error logging error: {e}")

    async def _write_log_entry(self, filename: str, entry: Dict):
        """Write log entry to file"""
        try:
            log_file = self.log_dir / filename

            async with aiofiles.open(log_file, 'a', encoding='utf-8') as f:
                await f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"Error writing log entry: {e}")

    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        try:
            # Calculate averages
            cpu_avg = sum(self.system_health["cpu_usage"][-10:]) / max(1, len(self.system_health["cpu_usage"][-10:]))
            memory_avg = sum(self.system_health["memory_usage"][-10:]) / max(1, len(self.system_health["memory_usage"][-10:]))
            disk_avg = sum(self.system_health["disk_usage"][-10:]) / max(1, len(self.system_health["disk_usage"][-10:]))

            return {
                "status": "healthy" if self.system_health["redis_connection"] else "degraded",
                "cpu_usage_percent": cpu_avg,
                "memory_usage_percent": memory_avg,
                "disk_usage_percent": disk_avg,
                "redis_connected": self.system_health["redis_connection"],
                "last_health_check": self.system_health["last_health_check"],
                "active_alerts": len([a for a in self.active_alerts.values() if not a.resolved]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def get_performance_metrics(self, time_range_hours: int = 1) -> Dict[str, Any]:
        """Get performance metrics for specified time range"""
        try:
            # Get metrics from Redis
            cutoff_time = time.time() - (time_range_hours * 3600)

            # Get all metric keys
            pattern = "metrics:*"
            keys = await self.redis.keys(pattern)

            metrics_summary = defaultdict(lambda: {
                "count": 0, "sum": 0, "avg": 0, "min": float('inf'), "max": 0
            })

            for key in keys:
                data = await self.redis.get(key)
                if data:
                    try:
                        metrics_data = json.loads(data)
                        metric_name = key.decode().split(":")[1]

                        summary = metrics_summary[metric_name]
                        summary["count"] += metrics_data.get("count", 0)
                        summary["sum"] += metrics_data.get("sum", 0)
                        summary["min"] = min(summary["min"], metrics_data.get("min", 0))
                        summary["max"] = max(summary["max"], metrics_data.get("max", 0))

                    except Exception as e:
                        logger.warning(f"Error processing metric {key}: {e}")

            # Calculate averages
            for name, summary in metrics_summary.items():
                if summary["count"] > 0:
                    summary["avg"] = summary["sum"] / summary["count"]

            return {
                "time_range_hours": time_range_hours,
                "metrics": dict(metrics_summary),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

    async def get_active_alerts(self) -> List[Dict]:
        """Get list of active (unresolved) alerts"""
        try:
            active_alerts = []
            for alert in self.active_alerts.values():
                if not alert.resolved:
                    active_alerts.append(asdict(alert))

            return active_alerts

        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    async def generate_report(self, report_type: str = "daily") -> Dict[str, Any]:
        """Generate comprehensive system report"""
        try:
            report = {
                "report_type": report_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "system_health": await self.get_system_health(),
                "performance_metrics": await self.get_performance_metrics(),
                "active_alerts": await self.get_active_alerts(),
                "summary": {}
            }

            # Generate summary
            health = report["system_health"]
            metrics = report["performance_metrics"]

            report["summary"] = {
                "overall_status": health.get("status", "unknown"),
                "active_alerts_count": len(report["active_alerts"]),
                "cpu_usage": health.get("cpu_usage_percent", 0),
                "memory_usage": health.get("memory_usage_percent", 0),
                "redis_connected": health.get("redis_connected", False)
            }

            # Save report to file
            report_filename = f"{report_type}_report_{int(time.time())}.json"
            report_path = self.log_dir / report_filename

            async with aiofiles.open(report_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report, ensure_ascii=False, indent=2))

            report["report_file"] = str(report_path)

            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
