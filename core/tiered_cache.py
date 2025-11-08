"""
分级缓存机制
实现多级缓存策略，为不同类型的数据提供不同的缓存策略

缓存层级：
- L1 (Hot): 热数据，TTL=10s，高频访问
- L2 (Warm): 温数据，TTL=60s，常规访问
- L3 (Cold): 冷数据，TTL=300s，低频访问
"""

import time
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

from src.common.logger import get_logger

logger = get_logger("tiered_cache")


class CacheTier(Enum):
    """缓存层级"""
    L1_HOT = "l1_hot"        # 热数据：10秒TTL
    L2_WARM = "l2_warm"      # 温数据：60秒TTL
    L3_COLD = "l3_cold"      # 冷数据：300秒TTL


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    timestamp: float
    tier: CacheTier
    access_count: int = 0
    last_access_time: float = 0.0

    def __post_init__(self):
        if self.last_access_time == 0.0:
            self.last_access_time = self.timestamp

    def is_expired(self, ttl: float) -> bool:
        """检查是否过期"""
        return time.time() - self.timestamp > ttl

    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_access_time = time.time()


class TieredCache:
    """分级缓存管理器"""

    # 各层级的TTL配置（秒）
    TIER_TTL = {
        CacheTier.L1_HOT: 10,
        CacheTier.L2_WARM: 60,
        CacheTier.L3_COLD: 300,
    }

    # 各层级的容量限制
    TIER_CAPACITY = {
        CacheTier.L1_HOT: 50,
        CacheTier.L2_WARM: 200,
        CacheTier.L3_COLD: 500,
    }

    def __init__(self):
        """初始化分级缓存"""
        # 每个层级使用独立的OrderedDict实现LRU
        self.caches: Dict[CacheTier, OrderedDict] = {
            CacheTier.L1_HOT: OrderedDict(),
            CacheTier.L2_WARM: OrderedDict(),
            CacheTier.L3_COLD: OrderedDict(),
        }

        # 统计信息
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
            "evictions": 0,
            "promotions": 0,  # L2->L1或L3->L2的提升次数
            "demotions": 0,   # L1->L2或L2->L3的降级次数
        }

        logger.info("分级缓存管理器初始化完成")

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        获取缓存值（自动处理层级提升）

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        # 从L1到L3依次查找
        for tier in [CacheTier.L1_HOT, CacheTier.L2_WARM, CacheTier.L3_COLD]:
            cache = self.caches[tier]

            if key in cache:
                entry = cache[key]
                ttl = self.TIER_TTL[tier]

                # 检查是否过期
                if entry.is_expired(ttl):
                    del cache[key]
                    continue

                # 记录访问
                entry.access()

                # 更新LRU顺序
                cache.move_to_end(key)

                # 记录命中统计
                if tier == CacheTier.L1_HOT:
                    self.stats["l1_hits"] += 1
                elif tier == CacheTier.L2_WARM:
                    self.stats["l2_hits"] += 1
                else:
                    self.stats["l3_hits"] += 1

                # 自动提升热数据
                if tier != CacheTier.L1_HOT and entry.access_count >= 3:
                    self._promote_entry(key, entry, tier)

                return entry.value

        # 缓存未命中
        self.stats["misses"] += 1
        return default

    def set(self, key: str, value: Any, tier: CacheTier = CacheTier.L2_WARM):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            tier: 缓存层级（默认L2）
        """
        cache = self.caches[tier]

        # 创建缓存条目
        entry = CacheEntry(
            value=value,
            timestamp=time.time(),
            tier=tier,
        )

        # 如果key已存在于其他层级，先删除
        for t in CacheTier:
            if t != tier and key in self.caches[t]:
                del self.caches[t][key]

        # 添加到指定层级
        cache[key] = entry

        # 检查容量限制，执行LRU淘汰
        capacity = self.TIER_CAPACITY[tier]
        if len(cache) > capacity:
            # 淘汰最旧的条目
            oldest_key = next(iter(cache))
            evicted_entry = cache[oldest_key]
            del cache[oldest_key]

            self.stats["evictions"] += 1

            # 如果被淘汰的条目访问次数较多，降级到下一层
            if tier != CacheTier.L3_COLD and evicted_entry.access_count >= 2:
                self._demote_entry(oldest_key, evicted_entry, tier)

    def _promote_entry(self, key: str, entry: CacheEntry, from_tier: CacheTier):
        """
        提升缓存条目到更高层级

        Args:
            key: 缓存键
            entry: 缓存条目
            from_tier: 来源层级
        """
        # 确定目标层级
        if from_tier == CacheTier.L3_COLD:
            to_tier = CacheTier.L2_WARM
        elif from_tier == CacheTier.L2_WARM:
            to_tier = CacheTier.L1_HOT
        else:
            return  # L1已经是最高层级

        # 从原层级删除
        del self.caches[from_tier][key]

        # 重置访问计数（避免无限提升）
        entry.access_count = 0
        entry.tier = to_tier

        # 添加到目标层级
        self.caches[to_tier][key] = entry

        self.stats["promotions"] += 1
        logger.debug(f"缓存提升: {key} 从 {from_tier.value} 到 {to_tier.value}")

    def _demote_entry(self, key: str, entry: CacheEntry, from_tier: CacheTier):
        """
        降级缓存条目到更低层级

        Args:
            key: 缓存键
            entry: 缓存条目
            from_tier: 来源层级
        """
        # 确定目标层级
        if from_tier == CacheTier.L1_HOT:
            to_tier = CacheTier.L2_WARM
        elif from_tier == CacheTier.L2_WARM:
            to_tier = CacheTier.L3_COLD
        else:
            return  # L3已经是最低层级

        # 重置访问计数
        entry.access_count = 0
        entry.tier = to_tier
        entry.timestamp = time.time()  # 更新时间戳

        # 添加到目标层级
        self.caches[to_tier][key] = entry

        self.stats["demotions"] += 1
        logger.debug(f"缓存降级: {key} 从 {from_tier.value} 到 {to_tier.value}")

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        deleted = False
        for tier in CacheTier:
            if key in self.caches[tier]:
                del self.caches[tier][key]
                deleted = True
        return deleted

    def clear(self, tier: Optional[CacheTier] = None):
        """
        清空缓存

        Args:
            tier: 指定层级，None表示清空所有层级
        """
        if tier is None:
            for t in CacheTier:
                self.caches[t].clear()
            logger.info("所有缓存层级已清空")
        else:
            self.caches[tier].clear()
            logger.info(f"缓存层级 {tier.value} 已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_entries = sum(len(cache) for cache in self.caches.values())
        total_hits = self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["l3_hits"]
        total_requests = total_hits + self.stats["misses"]

        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "total_entries": total_entries,
            "l1_entries": len(self.caches[CacheTier.L1_HOT]),
            "l2_entries": len(self.caches[CacheTier.L2_WARM]),
            "l3_entries": len(self.caches[CacheTier.L3_COLD]),
            "total_hits": total_hits,
            "l1_hits": self.stats["l1_hits"],
            "l2_hits": self.stats["l2_hits"],
            "l3_hits": self.stats["l3_hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self.stats["evictions"],
            "promotions": self.stats["promotions"],
            "demotions": self.stats["demotions"],
        }

    def cleanup_expired(self) -> int:
        """
        清理所有过期的缓存条目

        Returns:
            清理的条目数量
        """
        cleaned_count = 0

        for tier in CacheTier:
            cache = self.caches[tier]
            ttl = self.TIER_TTL[tier]
            keys_to_remove = []

            for key, entry in cache.items():
                if entry.is_expired(ttl):
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del cache[key]
                cleaned_count += 1

        if cleaned_count > 0:
            logger.debug(f"清理了 {cleaned_count} 个过期缓存条目")

        return cleaned_count
