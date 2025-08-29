#!/usr/bin/env python3
"""
Performance Optimization Engine
Intelligent resource management, load balancing, and performance tuning
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import redis.asyncio as redis
import psutil

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    active_connections: int
    queue_size: int
    response_time_avg: float
    throughput: float

@dataclass
class OptimizationAction:
    """Performance optimization action"""
    action_id: str
    action_type: str
    description: str
    priority: str
    estimated_impact: float
    implemented: bool = False
    timestamp: float = None

class PerformanceOptimizer:
    """Intelligent performance optimization engine"""

    def __init__(self, redis_client: redis.Redis = None):
        self.redis = redis_client

        # Performance tracking
        self.metrics_history = []
        self.optimization_actions = []
        self.active_optimizations = {}

        # Configuration
        self.config = {
            "cpu_threshold": 80.0,      # CPU usage threshold for optimization
            "memory_threshold": 85.0,   # Memory usage threshold
            "response_time_target": 5.0, # Target response time in seconds
            "max_concurrent_requests": 10,
            "cache_ttl_optimization": True,
            "connection_pooling": True,
            "batch_processing": True
        }

        # Performance baselines
        self.baselines = {
            "cpu_usage": 70.0,
            "memory_usage": 75.0,
            "response_time": 3.0,
            "throughput": 100  # requests per minute
        }

    async def init(self):
        """Initialize performance optimizer"""
        if not self.redis:
            self.redis = redis.from_url('redis://localhost:6379/0')

        # Start optimization monitoring
        asyncio.create_task(self._performance_monitoring_loop())
        asyncio.create_task(self._optimization_loop())

        logger.info("✅ Performance optimizer initialized")

    async def _performance_monitoring_loop(self):
        """Continuous performance monitoring"""
        while True:
            try:
                await self._collect_performance_metrics()
                await asyncio.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(30)

    async def _collect_performance_metrics(self):
        """Collect current performance metrics"""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent

            # Application metrics
            active_connections = await self._get_active_connections()
            queue_size = await self._get_queue_size()
            response_time_avg = await self._calculate_avg_response_time()
            throughput = await self._calculate_throughput()

            # Create metrics snapshot
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                active_connections=active_connections,
                queue_size=queue_size,
                response_time_avg=response_time_avg,
                throughput=throughput
            )

            # Store metrics
            self.metrics_history.append(metrics)

            # Keep only last 100 measurements
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]

            # Check for optimization opportunities
            await self._analyze_performance_triggers(metrics)

        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")

    async def _get_active_connections(self) -> int:
        """Get number of active connections"""
        try:
            # This would be specific to your application
            # For now, return a placeholder
            return 0
        except Exception:
            return 0

    async def _get_queue_size(self) -> int:
        """Get current queue size"""
        try:
            # Check Redis for queued items
            queue_keys = await self.redis.keys("queue:*")
            total_queued = 0
            for key in queue_keys:
                queue_size = await self.redis.llen(key)
                total_queued += queue_size
            return total_queued
        except Exception:
            return 0

    async def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent metrics"""
        try:
            if not self.metrics_history:
                return 0.0

            recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
            if recent_metrics:
                return sum(m.response_time_avg for m in recent_metrics) / len(recent_metrics)
            return 0.0
        except Exception:
            return 0.0

    async def _calculate_throughput(self) -> float:
        """Calculate current throughput"""
        try:
            # Simple throughput calculation based on metrics
            if len(self.metrics_history) >= 2:
                recent = self.metrics_history[-1]
                previous = self.metrics_history[-2]
                time_diff = recent.timestamp - previous.timestamp

                if time_diff > 0:
                    throughput_change = (recent.throughput - previous.throughput) / time_diff
                    return max(0, previous.throughput + throughput_change)

            return self.baselines["throughput"]
        except Exception:
            return 0.0

    async def _analyze_performance_triggers(self, metrics: PerformanceMetrics):
        """Analyze metrics for optimization triggers"""
        actions = []

        # High CPU usage
        if metrics.cpu_usage > self.config["cpu_threshold"]:
            actions.append(OptimizationAction(
                action_id=f"cpu_opt_{int(metrics.timestamp)}",
                action_type="cpu_optimization",
                description="High CPU usage detected - implementing CPU optimization",
                priority="high",
                estimated_impact=0.3
            ))

        # High memory usage
        if metrics.memory_usage > self.config["memory_threshold"]:
            actions.append(OptimizationAction(
                action_id=f"mem_opt_{int(metrics.timestamp)}",
                action_type="memory_optimization",
                description="High memory usage detected - implementing memory optimization",
                priority="high",
                estimated_impact=0.4
            ))

        # Slow response time
        if metrics.response_time_avg > self.config["response_time_target"]:
            actions.append(OptimizationAction(
                action_id=f"resp_opt_{int(metrics.timestamp)}",
                action_type="response_time_optimization",
                description="Slow response time detected - optimizing response time",
                priority="medium",
                estimated_impact=0.2
            ))

        # Large queue
        if metrics.queue_size > 50:
            actions.append(OptimizationAction(
                action_id=f"queue_opt_{int(metrics.timestamp)}",
                action_type="queue_optimization",
                description="Large queue detected - optimizing queue processing",
                priority="medium",
                estimated_impact=0.25
            ))

        # Add actions to queue
        for action in actions:
            if action.action_id not in self.active_optimizations:
                self.optimization_actions.append(action)
                logger.info(f"🎯 Optimization opportunity identified: {action.description}")

    async def _optimization_loop(self):
        """Main optimization execution loop"""
        while True:
            try:
                await self._execute_pending_optimizations()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(60)

    async def _execute_pending_optimizations(self):
        """Execute pending optimization actions"""
        # Sort by priority and impact
        pending_actions = [a for a in self.optimization_actions if not a.implemented]
        pending_actions.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}[x.priority],
            -x.estimated_impact
        ))

        # Execute top priority actions
        for action in pending_actions[:3]:  # Execute up to 3 actions at once
            try:
                await self._execute_optimization_action(action)
                action.implemented = True
                action.timestamp = time.time()
                self.active_optimizations[action.action_id] = action

                logger.info(f"✅ Optimization implemented: {action.description}")

            except Exception as e:
                logger.error(f"Error executing optimization {action.action_id}: {e}")

    async def _execute_optimization_action(self, action: OptimizationAction):
        """Execute specific optimization action"""
        if action.action_type == "cpu_optimization":
            await self._optimize_cpu_usage()
        elif action.action_type == "memory_optimization":
            await self._optimize_memory_usage()
        elif action.action_type == "response_time_optimization":
            await self._optimize_response_time()
        elif action.action_type == "queue_optimization":
            await self._optimize_queue_processing()

    async def _optimize_cpu_usage(self):
        """Implement CPU usage optimizations"""
        try:
            # Reduce concurrent processing
            current_max = self.config["max_concurrent_requests"]
            self.config["max_concurrent_requests"] = max(1, int(current_max * 0.7))

            # Enable more aggressive caching
            await self.redis.set("optimization:cpu_mode", "true")
            await self.redis.expire("optimization:cpu_mode", 300)  # 5 minutes

            logger.info("⚡ CPU optimization: Reduced concurrent requests, enabled aggressive caching")

        except Exception as e:
            logger.error(f"Error in CPU optimization: {e}")

    async def _optimize_memory_usage(self):
        """Implement memory usage optimizations"""
        try:
            # Clear old cache entries
            await self._clear_old_cache_entries()

            # Reduce cache TTL
            await self.redis.set("optimization:memory_mode", "true")
            await self.redis.expire("optimization:memory_mode", 300)

            # Force garbage collection in Python
            import gc
            gc.collect()

            logger.info("🧠 Memory optimization: Cleared old cache, reduced TTL, forced GC")

        except Exception as e:
            logger.error(f"Error in memory optimization: {e}")

    async def _optimize_response_time(self):
        """Implement response time optimizations"""
        try:
            # Enable response caching
            await self.redis.set("optimization:fast_mode", "true")
            await self.redis.expire("optimization:fast_mode", 300)

            # Pre-warm connections
            await self._warm_up_connections()

            logger.info("⚡ Response time optimization: Enabled fast mode, warmed up connections")

        except Exception as e:
            logger.error(f"Error in response time optimization: {e}")

    async def _optimize_queue_processing(self):
        """Implement queue processing optimizations"""
        try:
            # Increase batch processing size
            await self.redis.set("optimization:batch_mode", "true")
            await self.redis.expire("optimization:batch_mode", 300)

            # Optimize queue processing
            await self._optimize_queue_workers()

            logger.info("📋 Queue optimization: Enabled batch mode, optimized workers")

        except Exception as e:
            logger.error(f"Error in queue optimization: {e}")

    async def _clear_old_cache_entries(self):
        """Clear old/unused cache entries"""
        try:
            # Clear old product cache
            old_product_keys = await self.redis.keys("product:*")
            for key in old_product_keys[:100]:  # Clear in batches
                await self.redis.delete(key)

            # Clear old search cache
            old_search_keys = await self.redis.keys("search_cache:*")
            for key in old_search_keys[:50]:
                await self.redis.delete(key)

            logger.info("🧹 Cleared old cache entries")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    async def _warm_up_connections(self):
        """Warm up database connections"""
        try:
            # Ping Redis to ensure connection
            await self.redis.ping()

            # Pre-load frequently accessed data
            await self.redis.get("optimization:fast_mode")  # This will cache the optimization flag

            logger.info("🔥 Warmed up connections")

        except Exception as e:
            logger.error(f"Error warming connections: {e}")

    async def _optimize_queue_workers(self):
        """Optimize queue worker configuration"""
        try:
            # Adjust worker count based on load
            current_load = len(self.metrics_history)
            if current_load > 20:
                worker_count = 2  # Reduce workers under high load
            else:
                worker_count = 4  # Default worker count

            await self.redis.set("optimization:worker_count", str(worker_count))
            await self.redis.expire("optimization:worker_count", 300)

            logger.info(f"👷 Optimized worker count to {worker_count}")

        except Exception as e:
            logger.error(f"Error optimizing workers: {e}")

    async def get_performance_status(self) -> Dict[str, Any]:
        """Get current performance status and recommendations"""
        try:
            if not self.metrics_history:
                return {"status": "no_data"}

            latest_metrics = self.metrics_history[-1]

            # Calculate performance score
            cpu_score = max(0, 1 - (latest_metrics.cpu_usage / 100))
            memory_score = max(0, 1 - (latest_metrics.memory_usage / 100))
            response_score = max(0, 1 - (latest_metrics.response_time_avg / 10))  # Normalize to 10s
            throughput_score = min(1, latest_metrics.throughput / self.baselines["throughput"])

            overall_score = (cpu_score + memory_score + response_score + throughput_score) / 4

            # Generate recommendations
            recommendations = []
            if latest_metrics.cpu_usage > 80:
                recommendations.append("Consider reducing concurrent requests")
            if latest_metrics.memory_usage > 85:
                recommendations.append("Memory usage high - consider cache cleanup")
            if latest_metrics.response_time_avg > 5:
                recommendations.append("Response time slow - check database queries")
            if latest_metrics.throughput < 50:
                recommendations.append("Throughput low - consider load balancer")

            return {
                "overall_score": overall_score,
                "latest_metrics": {
                    "cpu_usage": latest_metrics.cpu_usage,
                    "memory_usage": latest_metrics.memory_usage,
                    "response_time_avg": latest_metrics.response_time_avg,
                    "throughput": latest_metrics.throughput,
                    "queue_size": latest_metrics.queue_size,
                    "active_connections": latest_metrics.active_connections
                },
                "active_optimizations": [asdict(a) for a in self.active_optimizations.values()],
                "recommendations": recommendations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting performance status: {e}")
            return {"status": "error", "error": str(e)}

    async def reset_optimizations(self):
        """Reset all active optimizations"""
        try:
            # Reset configuration to defaults
            self.config["max_concurrent_requests"] = 10

            # Clear optimization flags
            optimization_keys = await self.redis.keys("optimization:*")
            for key in optimization_keys:
                await self.redis.delete(key)

            # Clear active optimizations
            self.active_optimizations.clear()

            logger.info("🔄 Reset all optimizations to default state")

        except Exception as e:
            logger.error(f"Error resetting optimizations: {e}")

    async def export_performance_report(self, filename: str = None) -> Dict[str, Any]:
        """Export comprehensive performance report"""
        try:
            if not filename:
                timestamp = int(time.time())
                filename = f"performance_report_{timestamp}.json"

            report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "performance_status": await self.get_performance_status(),
                "metrics_history": [asdict(m) for m in self.metrics_history[-50:]],  # Last 50 measurements
                "optimization_actions": [asdict(a) for a in self.optimization_actions[-20:]],  # Last 20 actions
                "configuration": self.config,
                "baselines": self.baselines
            }

            # Save to file
            import aiofiles
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report, ensure_ascii=False, indent=2))

            return {
                "success": True,
                "filename": filename,
                "report_summary": {
                    "metrics_collected": len(self.metrics_history),
                    "optimizations_applied": len(self.optimization_actions),
                    "current_score": report["performance_status"].get("overall_score", 0)
                }
            }

        except Exception as e:
            logger.error(f"Error exporting performance report: {e}")
            return {"success": False, "error": str(e)}
