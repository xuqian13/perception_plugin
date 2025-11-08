"""
用户状态感知模块
感知用户的活跃度、情绪倾向、意图等
"""

import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict, field
from collections import deque
from src.common.logger import get_logger

logger = get_logger("user_perception")


@dataclass
class UserActivity:
    """用户活动记录"""

    user_id: str
    timestamp: float
    message_length: int
    message_content: str = ""


@dataclass
class UserStatus:
    """用户状态数据类"""

    user_id: str = ""
    user_nickname: str = ""

    # 活跃度相关
    message_count_1h: int = 0  # 最近1小时消息数
    message_count_24h: int = 0  # 最近24小时消息数
    last_message_time: float = 0.0
    avg_message_interval: float = 0.0  # 平均消息间隔（秒）
    activity_level: str = ""  # "very_active" | "active" | "normal" | "inactive" | "silent"

    # 消息特征
    avg_message_length: float = 0.0
    total_characters: int = 0

    # 情绪倾向（简单分析）
    emotion_tendency: str = "neutral"  # "positive" | "neutral" | "negative"
    emotion_score: float = 0.0  # -1.0 到 1.0

    # 互动倾向
    mention_count: int = 0  # 被提及次数
    reply_count: int = 0  # 回复次数
    interactivity: str = "normal"  # "high" | "normal" | "low"

    # 时间戳
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的用户状态摘要"""
        parts = []

        # 活跃度描述
        activity_desc = {
            "very_active": "非常活跃",
            "active": "很活跃",
            "normal": "正常活跃",
            "inactive": "不太活跃",
            "silent": "沉默",
        }
        parts.append(f"{self.user_nickname}{activity_desc.get(self.activity_level, '正常')}")

        # 最近活动
        if self.last_message_time > 0:
            time_since = time.time() - self.last_message_time
            if time_since < 60:
                parts.append("刚刚发言")
            elif time_since < 3600:
                parts.append(f"{int(time_since / 60)}分钟前发言")
            elif time_since < 86400:
                parts.append(f"{int(time_since / 3600)}小时前发言")

        return "，".join(parts)


class UserPerception:
    """用户状态感知器"""

    def __init__(self, history_window: int = 86400):
        """
        初始化用户感知器

        Args:
            history_window: 历史窗口大小（秒），默认24小时
        """
        self.history_window = history_window
        self.user_activities: Dict[str, deque] = {}  # user_id -> deque of UserActivity
        self.user_cache: Dict[str, UserStatus] = {}  # 用户状态缓存

        logger.info("用户感知模块初始化完成")

    def record_user_activity(
        self,
        user_id: str,
        message_content: str,
        timestamp: Optional[float] = None,
    ):
        """
        记录用户活动

        Args:
            user_id: 用户ID
            message_content: 消息内容
            timestamp: 时间戳，默认为当前时间
        """
        if timestamp is None:
            timestamp = time.time()

        activity = UserActivity(
            user_id=user_id,
            timestamp=timestamp,
            message_length=len(message_content),
            message_content=message_content,
        )

        if user_id not in self.user_activities:
            self.user_activities[user_id] = deque(maxlen=1000)  # 最多保存1000条记录

        self.user_activities[user_id].append(activity)

        # 清理过期数据
        self._cleanup_old_activities(user_id)

    def _cleanup_old_activities(self, user_id: str):
        """清理过期的活动记录"""
        if user_id not in self.user_activities:
            return

        current_time = time.time()
        cutoff_time = current_time - self.history_window

        activities = self.user_activities[user_id]
        while activities and activities[0].timestamp < cutoff_time:
            activities.popleft()

    def _get_user_activities(self, user_id: str, time_window: float) -> List[UserActivity]:
        """
        获取指定时间窗口内的用户活动

        Args:
            user_id: 用户ID
            time_window: 时间窗口（秒）

        Returns:
            活动列表
        """
        if user_id not in self.user_activities:
            return []

        current_time = time.time()
        cutoff_time = current_time - time_window

        activities = self.user_activities[user_id]
        return [act for act in activities if act.timestamp >= cutoff_time]

    def _calculate_activity_level(self, message_count_1h: int, message_count_24h: int) -> str:
        """
        计算活跃度等级

        Args:
            message_count_1h: 1小时内消息数
            message_count_24h: 24小时内消息数

        Returns:
            活跃度等级
        """
        if message_count_1h >= 20 or message_count_24h >= 100:
            return "very_active"
        elif message_count_1h >= 10 or message_count_24h >= 50:
            return "active"
        elif message_count_1h >= 3 or message_count_24h >= 10:
            return "normal"
        elif message_count_24h > 0:
            return "inactive"
        else:
            return "silent"

    def _analyze_emotion_tendency(self, messages: List[str]) -> tuple[str, float]:
        """
        分析情绪倾向（简单版本）

        Args:
            messages: 消息列表

        Returns:
            (情绪类型, 情绪分数)
        """
        # 简单的情绪关键词分析
        positive_keywords = ["哈哈", "😄", "😊", "😂", "👍", "棒", "好", "赞", "喜欢", "开心", "快乐"]
        negative_keywords = ["😢", "😭", "😞", "难过", "伤心", "烦", "讨厌", "不好", "糟糕"]

        positive_count = 0
        negative_count = 0

        for msg in messages:
            for keyword in positive_keywords:
                positive_count += msg.count(keyword)
            for keyword in negative_keywords:
                negative_count += msg.count(keyword)

        total = positive_count + negative_count
        if total == 0:
            return "neutral", 0.0

        score = (positive_count - negative_count) / total

        if score > 0.3:
            return "positive", score
        elif score < -0.3:
            return "negative", score
        else:
            return "neutral", score

    def get_user_status(self, user_id: str, user_nickname: str = "") -> UserStatus:
        """
        获取用户状态

        Args:
            user_id: 用户ID
            user_nickname: 用户昵称

        Returns:
            UserStatus对象
        """
        # 清理旧数据
        self._cleanup_old_activities(user_id)

        # 获取不同时间窗口的活动
        activities_1h = self._get_user_activities(user_id, 3600)
        activities_24h = self._get_user_activities(user_id, 86400)

        # 计算统计数据
        message_count_1h = len(activities_1h)
        message_count_24h = len(activities_24h)

        last_message_time = 0.0
        if activities_24h:
            last_message_time = activities_24h[-1].timestamp

        # 计算平均消息间隔
        avg_interval = 0.0
        if len(activities_24h) > 1:
            time_span = activities_24h[-1].timestamp - activities_24h[0].timestamp
            avg_interval = time_span / (len(activities_24h) - 1)

        # 计算平均消息长度
        avg_length = 0.0
        total_chars = 0
        if activities_24h:
            total_chars = sum(act.message_length for act in activities_24h)
            avg_length = total_chars / len(activities_24h)

        # 活跃度等级
        activity_level = self._calculate_activity_level(message_count_1h, message_count_24h)

        # 情绪分析
        recent_messages = [act.message_content for act in activities_1h[-10:]]  # 最近10条消息
        emotion_tendency, emotion_score = self._analyze_emotion_tendency(recent_messages)

        # 互动性分析（简化版）
        mention_count = sum(1 for act in activities_24h if "@" in act.message_content)
        interactivity = "high" if mention_count > 5 else "normal" if mention_count > 0 else "low"

        return UserStatus(
            user_id=user_id,
            user_nickname=user_nickname,
            message_count_1h=message_count_1h,
            message_count_24h=message_count_24h,
            last_message_time=last_message_time,
            avg_message_interval=avg_interval,
            activity_level=activity_level,
            avg_message_length=avg_length,
            total_characters=total_chars,
            emotion_tendency=emotion_tendency,
            emotion_score=emotion_score,
            mention_count=mention_count,
            reply_count=0,  # TODO: 需要消息上下文分析
            interactivity=interactivity,
            timestamp=time.time(),
        )

    def get_multiple_users_status(self, user_ids: List[str]) -> Dict[str, UserStatus]:
        """
        批量获取多个用户的状态

        Args:
            user_ids: 用户ID列表

        Returns:
            用户状态字典
        """
        return {user_id: self.get_user_status(user_id) for user_id in user_ids}
