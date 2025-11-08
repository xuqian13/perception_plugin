"""
行为模式感知模块
分析用户的在线习惯、作息规律、消息节奏等行为模式
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from src.common.logger import get_logger

logger = get_logger("behavior_pattern_perception")


@dataclass
class BehaviorPattern:
    """用户行为模式数据类"""

    user_id: str = ""
    user_nickname: str = ""

    # 在线时间模式（24小时，每小时的活跃度）
    hourly_activity: Dict[int, int] = None  # {0-23: message_count}
    most_active_hours: List[int] = None  # 最活跃的时段
    least_active_hours: List[int] = None  # 最不活跃的时段

    # 作息类型
    chronotype: str = "unknown"  # "early_bird" | "night_owl" | "regular" | "unknown"
    peak_activity_time: str = ""  # "morning" | "afternoon" | "evening" | "night"

    # 消息节奏
    avg_messages_per_day: float = 0.0
    avg_messages_per_hour_when_active: float = 0.0
    message_burst_tendency: float = 0.0  # 爆发式发言倾向 0.0-1.0

    # 话题偏好（最常讨论的话题）
    favorite_topics: List[str] = None
    topic_diversity: float = 0.0  # 话题多样性 0.0-1.0

    # 周期性行为
    weekly_pattern: Dict[int, int] = None  # {0-6: message_count} 周一到周日
    has_weekend_pattern: bool = False  # 是否有明显的周末模式
    weekend_activity_ratio: float = 1.0  # 周末/工作日活跃度比

    # 互动偏好
    preferred_interaction_users: List[str] = None  # 最常互动的用户
    group_participation_rate: float = 0.0  # 群聊参与率

    # 时间戳
    timestamp: float = 0.0
    data_points: int = 0  # 数据点数量（消息数）

    def __post_init__(self):
        if self.hourly_activity is None:
            self.hourly_activity = {}
        if self.most_active_hours is None:
            self.most_active_hours = []
        if self.least_active_hours is None:
            self.least_active_hours = []
        if self.favorite_topics is None:
            self.favorite_topics = []
        if self.weekly_pattern is None:
            self.weekly_pattern = {}
        if self.preferred_interaction_users is None:
            self.preferred_interaction_users = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的行为模式摘要"""
        parts = []

        # 作息类型
        chronotype_desc = {
            "early_bird": "早起型",
            "night_owl": "夜猫子型",
            "regular": "正常作息",
            "unknown": "作息不规律",
        }
        parts.append(f"{self.user_nickname or '用户'}是{chronotype_desc.get(self.chronotype, '作息不规律')}")

        # 活跃时段
        if self.most_active_hours:
            hours_str = "、".join([f"{h}点" for h in self.most_active_hours[:3]])
            parts.append(f"通常在{hours_str}最活跃")

        # 日均消息
        if self.avg_messages_per_day > 0:
            parts.append(f"日均发送{self.avg_messages_per_day:.1f}条消息")

        # 话题偏好
        if self.favorite_topics:
            topics_str = "、".join(self.favorite_topics[:3])
            parts.append(f"常聊{topics_str}")

        return "，".join(parts)


class BehaviorPatternPerception:
    """行为模式感知器"""

    def __init__(self, history_days: int = 30):
        """
        初始化行为模式感知器

        Args:
            history_days: 历史分析天数
        """
        self.history_days = history_days
        self.user_messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 每条消息记录: {"timestamp": float, "hour": int, "weekday": int, "content": str, "chat_id": str}

        logger.info(f"行为模式感知模块初始化完成，历史分析天数: {history_days}")

    def record_message(
        self,
        user_id: str,
        message_content: str,
        chat_id: str = "",
        timestamp: Optional[float] = None,
    ):
        """
        记录用户消息

        Args:
            user_id: 用户ID
            message_content: 消息内容
            chat_id: 聊天ID
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        dt = datetime.fromtimestamp(timestamp)

        message_record = {
            "timestamp": timestamp,
            "hour": dt.hour,
            "weekday": dt.weekday(),
            "content": message_content,
            "chat_id": chat_id,
        }

        self.user_messages[user_id].append(message_record)

        # 清理过期数据
        self._cleanup_old_messages(user_id)

    def _cleanup_old_messages(self, user_id: str):
        """清理过期消息"""
        if user_id not in self.user_messages:
            return

        cutoff_time = time.time() - (self.history_days * 86400)
        self.user_messages[user_id] = [
            msg for msg in self.user_messages[user_id]
            if msg["timestamp"] >= cutoff_time
        ]

    def _analyze_hourly_activity(self, messages: List[Dict]) -> Dict[int, int]:
        """分析每小时活跃度"""
        hourly_count = defaultdict(int)
        for msg in messages:
            hourly_count[msg["hour"]] += 1
        return dict(hourly_count)

    def _analyze_chronotype(self, hourly_activity: Dict[int, int]) -> tuple[str, str]:
        """
        分析作息类型

        Returns:
            (chronotype, peak_activity_time)
        """
        if not hourly_activity:
            return "unknown", ""

        # 计算不同时段的活跃度
        morning_hours = [6, 7, 8, 9, 10]  # 早晨
        afternoon_hours = [11, 12, 13, 14, 15, 16, 17]  # 下午
        evening_hours = [18, 19, 20, 21, 22]  # 晚上
        night_hours = [23, 0, 1, 2, 3, 4, 5]  # 深夜

        morning_activity = sum(hourly_activity.get(h, 0) for h in morning_hours)
        afternoon_activity = sum(hourly_activity.get(h, 0) for h in afternoon_hours)
        evening_activity = sum(hourly_activity.get(h, 0) for h in evening_hours)
        night_activity = sum(hourly_activity.get(h, 0) for h in night_hours)

        # 找出最活跃时段
        activities = {
            "morning": morning_activity,
            "afternoon": afternoon_activity,
            "evening": evening_activity,
            "night": night_activity,
        }
        peak_time = max(activities, key=activities.get)

        # 判断作息类型
        total_activity = sum(activities.values())
        if total_activity == 0:
            return "unknown", ""

        morning_ratio = morning_activity / total_activity
        night_ratio = night_activity / total_activity

        if morning_ratio > 0.35:
            chronotype = "early_bird"
        elif night_ratio > 0.35:
            chronotype = "night_owl"
        else:
            chronotype = "regular"

        return chronotype, peak_time

    def _get_most_active_hours(self, hourly_activity: Dict[int, int], top_n: int = 3) -> List[int]:
        """获取最活跃的N个小时"""
        sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)
        return [hour for hour, count in sorted_hours[:top_n]]

    def _get_least_active_hours(self, hourly_activity: Dict[int, int], bottom_n: int = 3) -> List[int]:
        """获取最不活跃的N个小时"""
        # 只考虑有消息的小时
        if not hourly_activity:
            return []
        sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1])
        return [hour for hour, count in sorted_hours[:bottom_n]]

    def _analyze_message_rhythm(self, messages: List[Dict]) -> tuple[float, float, float]:
        """
        分析消息节奏

        Returns:
            (avg_per_day, avg_per_hour_when_active, burst_tendency)
        """
        if not messages:
            return 0.0, 0.0, 0.0

        # 日均消息数
        time_span_days = (messages[-1]["timestamp"] - messages[0]["timestamp"]) / 86400
        avg_per_day = len(messages) / max(1, time_span_days)

        # 计算活跃时段的平均每小时消息数
        hourly_count = defaultdict(int)
        for msg in messages:
            hourly_count[msg["hour"]] += 1

        active_hours = [count for count in hourly_count.values() if count > 0]
        avg_per_hour_when_active = sum(active_hours) / len(active_hours) if active_hours else 0.0

        # 爆发倾向：计算消息时间间隔的方差
        if len(messages) > 1:
            intervals = []
            for i in range(1, len(messages)):
                interval = messages[i]["timestamp"] - messages[i-1]["timestamp"]
                intervals.append(interval)

            avg_interval = sum(intervals) / len(intervals)
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            # 归一化到0-1
            burst_tendency = min(1.0, variance / (3600 * 3600))  # 以1小时为基准
        else:
            burst_tendency = 0.0

        return avg_per_day, avg_per_hour_when_active, burst_tendency

    def _extract_favorite_topics(self, messages: List[Dict], top_n: int = 5) -> tuple[List[str], float]:
        """
        提取最喜欢的话题

        Returns:
            (favorite_topics, topic_diversity)
        """
        # 简单的关键词提取（基于词频）
        from collections import Counter
        import re

        all_words = []
        for msg in messages:
            # 提取中文词（2-4字）和英文单词
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', msg["content"])
            english_words = re.findall(r'[a-zA-Z]{3,}', msg["content"].lower())
            all_words.extend(chinese_words + english_words)

        # 停用词过滤
        stopwords = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "这", "那", "和", "与"}
        all_words = [w for w in all_words if w not in stopwords]

        if not all_words:
            return [], 0.0

        word_freq = Counter(all_words)
        favorite_topics = [word for word, count in word_freq.most_common(top_n)]

        # 话题多样性：使用词汇多样性指标（unique words / total words）
        topic_diversity = len(set(all_words)) / len(all_words) if all_words else 0.0

        return favorite_topics, topic_diversity

    def _analyze_weekly_pattern(self, messages: List[Dict]) -> tuple[Dict[int, int], bool, float]:
        """
        分析周模式

        Returns:
            (weekly_pattern, has_weekend_pattern, weekend_ratio)
        """
        weekly_count = defaultdict(int)
        for msg in messages:
            weekly_count[msg["weekday"]] += 1

        # 计算周末/工作日比例
        weekday_activity = sum(weekly_count.get(i, 0) for i in range(5))  # 周一到周五
        weekend_activity = sum(weekly_count.get(i, 0) for i in [5, 6])  # 周六周日

        weekday_avg = weekday_activity / 5 if weekday_activity > 0 else 0
        weekend_avg = weekend_activity / 2 if weekend_activity > 0 else 0

        weekend_ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 1.0

        # 如果周末活跃度显著不同（>1.5倍或<0.5倍），认为有明显周末模式
        has_weekend_pattern = weekend_ratio > 1.5 or weekend_ratio < 0.5

        return dict(weekly_count), has_weekend_pattern, weekend_ratio

    def _analyze_interaction_preference(self, messages: List[Dict]) -> List[str]:
        """分析互动偏好（最常在哪些聊天中发言）"""
        chat_counts = Counter(msg["chat_id"] for msg in messages if msg["chat_id"])
        return [chat_id for chat_id, count in chat_counts.most_common(5)]

    def get_behavior_pattern(self, user_id: str, user_nickname: str = "") -> BehaviorPattern:
        """
        获取用户行为模式

        Args:
            user_id: 用户ID
            user_nickname: 用户昵称

        Returns:
            BehaviorPattern对象
        """
        messages = self.user_messages.get(user_id, [])

        if not messages:
            return BehaviorPattern(
                user_id=user_id,
                user_nickname=user_nickname,
                timestamp=time.time(),
                data_points=0,
            )

        # 分析各项指标
        hourly_activity = self._analyze_hourly_activity(messages)
        chronotype, peak_time = self._analyze_chronotype(hourly_activity)
        most_active_hours = self._get_most_active_hours(hourly_activity, 3)
        least_active_hours = self._get_least_active_hours(hourly_activity, 3)

        avg_per_day, avg_per_hour, burst_tendency = self._analyze_message_rhythm(messages)
        favorite_topics, topic_diversity = self._extract_favorite_topics(messages)
        weekly_pattern, has_weekend, weekend_ratio = self._analyze_weekly_pattern(messages)
        preferred_chats = self._analyze_interaction_preference(messages)

        return BehaviorPattern(
            user_id=user_id,
            user_nickname=user_nickname,
            hourly_activity=hourly_activity,
            most_active_hours=most_active_hours,
            least_active_hours=least_active_hours,
            chronotype=chronotype,
            peak_activity_time=peak_time,
            avg_messages_per_day=avg_per_day,
            avg_messages_per_hour_when_active=avg_per_hour,
            message_burst_tendency=burst_tendency,
            favorite_topics=favorite_topics,
            topic_diversity=topic_diversity,
            weekly_pattern=weekly_pattern,
            has_weekend_pattern=has_weekend,
            weekend_activity_ratio=weekend_ratio,
            preferred_interaction_users=preferred_chats,
            timestamp=time.time(),
            data_points=len(messages),
        )
