"""
感知插件性能监控和基准测试工具

提供：
1. 性能基准测试
2. 实时性能监控
3. 性能对比分析
"""

import time
import asyncio
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager

from src.common.logger import get_logger

logger = get_logger("perception_benchmark")


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    ops_per_sec: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  迭代次数: {self.iterations}\n"
            f"  总时间: {self.total_time:.4f}s\n"
            f"  平均时间: {self.avg_time*1000:.2f}ms\n"
            f"  最小时间: {self.min_time*1000:.2f}ms\n"
            f"  最大时间: {self.max_time*1000:.2f}ms\n"
            f"  吞吐量: {self.ops_per_sec:.2f} ops/s"
        )


class PerformanceTimer:
    """性能计时器"""

    def __init__(self):
        self.timings: List[float] = []
        self.start_time: float = 0.0

    @contextmanager
    def measure(self):
        """测量代码块执行时间"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.timings.append(elapsed)

    def get_stats(self) -> Dict[str, float]:
        """获取统计信息"""
        if not self.timings:
            return {
                "count": 0,
                "total": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
            }

        return {
            "count": len(self.timings),
            "total": sum(self.timings),
            "avg": sum(self.timings) / len(self.timings),
            "min": min(self.timings),
            "max": max(self.timings),
        }

    def reset(self):
        """重置计时器"""
        self.timings.clear()


class PerceptionBenchmark:
    """感知插件基准测试工具"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    async def benchmark_function(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        **kwargs
    ) -> BenchmarkResult:
        """
        基准测试函数

        Args:
            name: 测试名称
            func: 要测试的函数（可以是同步或异步）
            iterations: 迭代次数
            warmup: 预热次数
            **kwargs: 传递给函数的参数

        Returns:
            基准测试结果
        """
        logger.info(f"开始基准测试: {name} (迭代{iterations}次)")

        # 判断是否为协程函数
        is_async = asyncio.iscoroutinefunction(func)

        # 预热
        for _ in range(warmup):
            if is_async:
                await func(**kwargs)
            else:
                func(**kwargs)

        # 正式测试
        timings = []
        start_time = time.perf_counter()

        for i in range(iterations):
            iteration_start = time.perf_counter()

            if is_async:
                await func(**kwargs)
            else:
                func(**kwargs)

            iteration_time = time.perf_counter() - iteration_start
            timings.append(iteration_time)

        total_time = time.perf_counter() - start_time

        # 计算统计信息
        avg_time = sum(timings) / len(timings)
        min_time = min(timings)
        max_time = max(timings)
        ops_per_sec = iterations / total_time

        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            ops_per_sec=ops_per_sec,
        )

        self.results.append(result)
        logger.info(f"完成基准测试: {name}")
        logger.info(str(result))

        return result

    async def benchmark_cache_operations(self, perception_manager) -> Dict[str, BenchmarkResult]:
        """
        测试缓存操作性能

        Args:
            perception_manager: 感知管理器实例

        Returns:
            测试结果字典
        """
        logger.info("开始缓存操作性能测试")

        results = {}

        # 测试1: 缓存写入
        async def cache_write_test():
            snapshot = await perception_manager.get_perception_snapshot(
                chat_id="test_chat",
                user_ids=["user1", "user2"],
                use_cache=False
            )

        results["cache_write"] = await self.benchmark_function(
            "缓存写入",
            cache_write_test,
            iterations=100
        )

        # 测试2: 缓存读取（命中）
        # 先写入一次确保缓存存在
        await perception_manager.get_perception_snapshot(
            chat_id="test_chat_read",
            user_ids=["user1"],
            use_cache=True
        )

        async def cache_read_test():
            await perception_manager.get_perception_snapshot(
                chat_id="test_chat_read",
                user_ids=["user1"],
                use_cache=True
            )

        results["cache_hit"] = await self.benchmark_function(
            "缓存读取（命中）",
            cache_read_test,
            iterations=1000
        )

        # 测试3: 缓存失效
        def cache_invalidation_test():
            perception_manager._invalidate_related_cache("test_chat", "user1")

        results["cache_invalidation"] = await self.benchmark_function(
            "缓存失效",
            cache_invalidation_test,
            iterations=100
        )

        return results

    async def benchmark_device_perception(self, device_perception) -> Dict[str, BenchmarkResult]:
        """
        测试设备感知性能

        Args:
            device_perception: 设备感知实例

        Returns:
            测试结果字典
        """
        logger.info("开始设备感知性能测试")

        results = {}

        # 测试CPU信息获取（优化后应该非常快）
        def get_cpu_test():
            device_perception.get_cpu_info()

        results["cpu_info"] = await self.benchmark_function(
            "CPU信息获取",
            get_cpu_test,
            iterations=1000
        )

        # 测试内存信息获取
        def get_memory_test():
            device_perception.get_memory_info()

        results["memory_info"] = await self.benchmark_function(
            "内存信息获取",
            get_memory_test,
            iterations=1000
        )

        # 测试完整设备状态获取
        def get_device_status_test():
            device_perception.get_device_status()

        results["device_status"] = await self.benchmark_function(
            "完整设备状态获取",
            get_device_status_test,
            iterations=100
        )

        return results

    async def benchmark_message_processing(self, perception_manager) -> BenchmarkResult:
        """
        测试消息处理性能

        Args:
            perception_manager: 感知管理器实例

        Returns:
            测试结果
        """
        logger.info("开始消息处理性能测试")

        def process_message_test():
            perception_manager.record_user_message(
                chat_id="benchmark_chat",
                user_id="benchmark_user",
                message_content="这是一条测试消息",
                user_nickname="测试用户"
            )

        result = await self.benchmark_function(
            "消息处理",
            process_message_test,
            iterations=1000
        )

        return result

    def compare_results(self, before: BenchmarkResult, after: BenchmarkResult) -> Dict[str, Any]:
        """
        对比优化前后的结果

        Args:
            before: 优化前的结果
            after: 优化后的结果

        Returns:
            对比分析
        """
        improvement_avg = ((before.avg_time - after.avg_time) / before.avg_time) * 100
        improvement_ops = ((after.ops_per_sec - before.ops_per_sec) / before.ops_per_sec) * 100

        return {
            "name": after.name,
            "avg_time_before": before.avg_time * 1000,  # ms
            "avg_time_after": after.avg_time * 1000,    # ms
            "improvement_avg": improvement_avg,         # %
            "ops_before": before.ops_per_sec,
            "ops_after": after.ops_per_sec,
            "improvement_ops": improvement_ops,         # %
        }

    def generate_report(self) -> str:
        """生成性能测试报告"""
        if not self.results:
            return "暂无性能测试结果"

        lines = ["=" * 60]
        lines.append("感知插件性能测试报告")
        lines.append("=" * 60)
        lines.append("")

        for i, result in enumerate(self.results, 1):
            lines.append(f"{i}. {result.name}")
            lines.append(f"   迭代次数: {result.iterations}")
            lines.append(f"   平均时间: {result.avg_time*1000:.2f} ms")
            lines.append(f"   最小时间: {result.min_time*1000:.2f} ms")
            lines.append(f"   最大时间: {result.max_time*1000:.2f} ms")
            lines.append(f"   吞吐量: {result.ops_per_sec:.2f} ops/s")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)


# 便捷的性能计时装饰器
class PerformanceMonitor:
    """性能监控器（装饰器模式）"""

    _timers: Dict[str, PerformanceTimer] = {}

    @classmethod
    @contextmanager
    def measure(cls, name: str):
        """测量代码块性能"""
        if name not in cls._timers:
            cls._timers[name] = PerformanceTimer()

        timer = cls._timers[name]
        with timer.measure():
            yield

    @classmethod
    def get_stats(cls, name: str) -> Dict[str, float]:
        """获取性能统计"""
        if name not in cls._timers:
            return {}
        return cls._timers[name].get_stats()

    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, float]]:
        """获取所有性能统计"""
        return {
            name: timer.get_stats()
            for name, timer in cls._timers.items()
        }

    @classmethod
    def reset(cls, name: str = None):
        """重置计时器"""
        if name is None:
            for timer in cls._timers.values():
                timer.reset()
        elif name in cls._timers:
            cls._timers[name].reset()
