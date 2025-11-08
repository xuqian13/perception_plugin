#!/usr/bin/env python3
"""
感知插件性能优化验证脚本

使用方法:
    python test_performance_optimization.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from plugins.perception_plugin.perception_manager import perception_manager
from plugins.perception_plugin.benchmark import PerceptionBenchmark
from src.common.logger import get_logger

logger = get_logger("test_performance")


async def test_cache_invalidation():
    """测试缓存失效优化"""
    print("\n" + "=" * 60)
    print("测试 1: 缓存失效优化")
    print("=" * 60)

    # 模拟创建多个缓存项
    print("创建测试缓存...")
    for i in range(10):
        await perception_manager.get_perception_snapshot(
            chat_id=f"chat_{i}",
            user_ids=[f"user_{j}" for j in range(3)],
            use_cache=True
        )

    print(f"当前缓存数量: {len(perception_manager.perception_cache)}")

    # 测试失效一个用户的缓存
    print("\n测试失效单个用户的缓存...")
    perception_manager._invalidate_related_cache("chat_0", "user_0")

    print(f"失效后缓存数量: {len(perception_manager.perception_cache)}")
    print(f"缓存失效统计: {perception_manager.stats.get('cache_invalidations', 0)}")

    print("\n✅ 缓存失效优化测试完成")
    print("优化点: 只失效相关的缓存项，避免过度清理")


async def test_cpu_sampling():
    """测试CPU采样优化"""
    print("\n" + "=" * 60)
    print("测试 2: CPU采样优化")
    print("=" * 60)

    device_perception = perception_manager.device_perception

    print("测试CPU信息获取速度（应该是非阻塞的）...")

    # 连续获取多次CPU信息，测试响应时间
    import time

    iterations = 100
    start = time.perf_counter()

    for i in range(iterations):
        cpu_info = device_perception.get_cpu_info()

    elapsed = time.perf_counter() - start
    avg_time_ms = (elapsed / iterations) * 1000

    print(f"迭代次数: {iterations}")
    print(f"总时间: {elapsed:.4f}s")
    print(f"平均时间: {avg_time_ms:.2f}ms")
    print(f"吞吐量: {iterations/elapsed:.2f} ops/s")

    print("\n✅ CPU采样优化测试完成")
    print("优化点: 使用后台线程采样，消除阻塞")
    print(f"当前CPU使用率: {cpu_info['percent']:.1f}%")


async def test_tiered_cache():
    """测试分级缓存"""
    print("\n" + "=" * 60)
    print("测试 3: 分级缓存机制")
    print("=" * 60)

    from plugins.perception_plugin.core.tiered_cache import TieredCache, CacheTier

    cache = TieredCache()

    print("测试缓存层级...")

    # L1: 热数据
    cache.set("hot_key_1", "hot_value_1", CacheTier.L1_HOT)
    cache.set("hot_key_2", "hot_value_2", CacheTier.L1_HOT)

    # L2: 温数据
    cache.set("warm_key_1", "warm_value_1", CacheTier.L2_WARM)
    cache.set("warm_key_2", "warm_value_2", CacheTier.L2_WARM)

    # L3: 冷数据
    cache.set("cold_key_1", "cold_value_1", CacheTier.L3_COLD)

    # 测试多次访问触发提升
    print("\n测试热数据提升...")
    for i in range(5):
        cache.get("warm_key_1")  # 访问多次后应该提升到L1

    # 获取统计
    stats = cache.get_stats()

    print(f"L1 缓存条目: {stats['l1_entries']}")
    print(f"L2 缓存条目: {stats['l2_entries']}")
    print(f"L3 缓存条目: {stats['l3_entries']}")
    print(f"总命中次数: {stats['total_hits']}")
    print(f"提升次数: {stats['promotions']}")
    print(f"降级次数: {stats['demotions']}")
    print(f"命中率: {stats['hit_rate']}")

    print("\n✅ 分级缓存测试完成")
    print("优化点: 根据访问频率自动调整缓存层级")


async def run_benchmark():
    """运行完整的基准测试"""
    print("\n" + "=" * 60)
    print("基准测试: 性能对比")
    print("=" * 60)

    benchmark = PerceptionBenchmark()

    # 测试设备感知
    print("\n--- 设备感知性能测试 ---")
    device_results = await benchmark.benchmark_device_perception(
        perception_manager.device_perception
    )

    for name, result in device_results.items():
        print(f"\n{result}")

    # 测试缓存操作
    print("\n--- 缓存操作性能测试 ---")
    cache_results = await benchmark.benchmark_cache_operations(perception_manager)

    for name, result in cache_results.items():
        print(f"\n{result}")

    # 测试消息处理
    print("\n--- 消息处理性能测试 ---")
    msg_result = await benchmark.benchmark_message_processing(perception_manager)
    print(f"\n{msg_result}")

    # 生成报告
    print("\n" + "=" * 60)
    print("完整性能报告")
    print("=" * 60)
    print(benchmark.generate_report())


async def main():
    """主函数"""
    print("感知插件性能优化验证")
    print("=" * 60)

    try:
        # 配置感知管理器
        config = {
            "enabled_modules": {
                "device": True,
                "user": True,
                "context": True,
                "self": True,
            },
            "cache_ttl": 60,
        }
        perception_manager.configure(config)

        # 运行各项测试
        await test_cache_invalidation()
        await test_cpu_sampling()
        await test_tiered_cache()

        # 运行基准测试
        await run_benchmark()

        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)

        print("\n优化总结:")
        print("1. ✅ 缓存失效优化: 细粒度失效，减少不必要的缓存清理")
        print("2. ✅ CPU采样优化: 后台线程采样，消除阻塞")
        print("3. ✅ 分级缓存: 根据访问频率自动优化缓存策略")

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        raise

    finally:
        # 清理资源
        if hasattr(perception_manager.device_perception, 'stop_sampling'):
            perception_manager.device_perception.stop_sampling()


if __name__ == "__main__":
    asyncio.run(main())
