"""
事件序列感知模块
记录和分析重要事件、里程碑、周期性事件等
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import defaultdict
from src.common.logger import get_logger

logger = get_logger("event_sequence_perception")


@dataclass
class Event:
    """事件数据类"""

    event_id: str
    event_type: str  # "milestone" | "birthday" | "anniversary" | "custom"
    title: str
    description: str = ""
    timestamp: float = 0.0
    participants: List[str] = None  # 参与者user_id列表
    importance: int = 1  # 重要性 1-5
    tags: List[str] = None  # 标签
    recurrence: str = "none"  # "none" | "daily" | "weekly" | "monthly" | "yearly"
    chat_id: str = ""

    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.tags is None:
            self.tags = []


@dataclass
class EventSequenceStatus:
    """事件序列状态数据类"""

    chat_id: str = ""

    # 事件列表
    recent_events: List[Event] = None  # 最近事件
    upcoming_events: List[Event] = None  # 即将到来的事件
    milestone_events: List[Event] = None  # 里程碑事件

    # 统计
    total_events: int = 0
    events_this_month: int = 0
    events_this_week: int = 0

    # 周期性事件
    recurring_events: List[Event] = None  # 周期性事件
    next_recurring_event: Optional[Event] = None  # 下一个周期性事件

    # 时间线分析
    avg_event_interval_days: float = 0.0  # 平均事件间隔
    most_active_period: str = ""  # 最活跃时期

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.recent_events is None:
            self.recent_events = []
        if self.upcoming_events is None:
            self.upcoming_events = []
        if self.milestone_events is None:
            self.milestone_events = []
        if self.recurring_events is None:
            self.recurring_events = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        return data

    def get_human_readable_summary(self) -> str:
        """获取人类可读的事件序列摘要"""
        parts = []

        # 总事件数
        if self.total_events > 0:
            parts.append(f"共记录{self.total_events}个事件")

        # 最近事件
        if self.recent_events:
            latest = self.recent_events[0]
            parts.append(f"最近：{latest.title}")

        # 即将到来的事件
        if self.upcoming_events:
            next_event = self.upcoming_events[0]
            parts.append(f"即将：{next_event.title}")

        return "，".join(parts) if parts else "暂无事件记录"


class EventSequencePerception:
    """事件序列感知器"""

    def __init__(self, auto_detect: bool = True):
        """
        初始化事件序列感知器

        Args:
            auto_detect: 是否启用自动事件检测
        """
        # 存储事件
        # {chat_id: [Event, ...]}
        self.events: Dict[str, List[Event]] = defaultdict(list)

        # 是否启用自动检测
        self.auto_detect = auto_detect

        # 自动检测的事件类型
        self.auto_detect_keywords = {
            "birthday": ["生日", "birthday", "生辰"],
            "anniversary": ["周年", "纪念日", "anniversary"],
            "milestone": ["里程碑", "达成", "milestone", "成就"],
        }

        logger.info(f"事件序列感知模块初始化完成，自动检测: {'启用' if auto_detect else '禁用'}")

    def add_event(
        self,
        chat_id: str,
        event_type: str,
        title: str,
        description: str = "",
        timestamp: Optional[float] = None,
        participants: Optional[List[str]] = None,
        importance: int = 1,
        tags: Optional[List[str]] = None,
        recurrence: str = "none",
    ) -> str:
        """
        添加事件

        Args:
            chat_id: 聊天ID
            event_type: 事件类型
            title: 事件标题
            description: 事件描述
            timestamp: 事件时间戳
            participants: 参与者
            importance: 重要性 1-5
            tags: 标签
            recurrence: 重复模式

        Returns:
            event_id
        """
        if timestamp is None:
            timestamp = time.time()

        event_id = f"{chat_id}_{int(timestamp)}_{len(self.events[chat_id])}"

        event = Event(
            event_id=event_id,
            event_type=event_type,
            title=title,
            description=description,
            timestamp=timestamp,
            participants=participants or [],
            importance=importance,
            tags=tags or [],
            recurrence=recurrence,
            chat_id=chat_id,
        )

        self.events[chat_id].append(event)

        # 按时间排序
        self.events[chat_id].sort(key=lambda e: e.timestamp)

        logger.debug(f"添加事件: {title} ({event_type})")

        return event_id

    def auto_detect_event(
        self,
        chat_id: str,
        message_content: str,
        user_id: str,
        timestamp: Optional[float] = None,
    ):
        """
        自动检测消息中的事件

        Args:
            chat_id: 聊天ID
            message_content: 消息内容
            user_id: 用户ID
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        # 检测关键词
        for event_type, keywords in self.auto_detect_keywords.items():
            for keyword in keywords:
                if keyword in message_content:
                    # 自动创建事件
                    self.add_event(
                        chat_id=chat_id,
                        event_type=event_type,
                        title=message_content[:50],  # 使用消息前50字作为标题
                        description=message_content,
                        timestamp=timestamp,
                        participants=[user_id],
                        importance=2,
                        tags=["auto_detected"],
                        recurrence="none",
                    )
                    break

    def get_recent_events(self, chat_id: str, limit: int = 10) -> List[Event]:
        """获取最近事件"""
        events = self.events.get(chat_id, [])
        # 返回最近的N个事件
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_upcoming_events(self, chat_id: str, days_ahead: int = 30, limit: int = 5) -> List[Event]:
        """获取即将到来的事件"""
        now = time.time()
        future_time = now + (days_ahead * 86400)

        events = self.events.get(chat_id, [])
        upcoming = [e for e in events if now < e.timestamp <= future_time]

        return sorted(upcoming, key=lambda e: e.timestamp)[:limit]

    def get_milestone_events(self, chat_id: str) -> List[Event]:
        """获取里程碑事件"""
        events = self.events.get(chat_id, [])
        milestones = [e for e in events if e.event_type == "milestone"]
        return sorted(milestones, key=lambda e: e.timestamp, reverse=True)

    def get_recurring_events(self, chat_id: str) -> List[Event]:
        """获取周期性事件"""
        events = self.events.get(chat_id, [])
        return [e for e in events if e.recurrence != "none"]

    def _calculate_event_interval(self, events: List[Event]) -> float:
        """计算平均事件间隔（天）"""
        if len(events) < 2:
            return 0.0

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        intervals = []

        for i in range(1, len(sorted_events)):
            interval = sorted_events[i].timestamp - sorted_events[i-1].timestamp
            intervals.append(interval / 86400)  # 转换为天

        return sum(intervals) / len(intervals) if intervals else 0.0

    def _find_most_active_period(self, events: List[Event]) -> str:
        """找出最活跃的时期"""
        if not events:
            return ""

        # 按月份统计
        monthly_counts = defaultdict(int)

        for event in events:
            dt = datetime.fromtimestamp(event.timestamp)
            month_key = dt.strftime("%Y-%m")
            monthly_counts[month_key] += 1

        if not monthly_counts:
            return ""

        most_active_month = max(monthly_counts, key=monthly_counts.get)
        return most_active_month

    def get_event_sequence_status(self, chat_id: str) -> EventSequenceStatus:
        """
        获取事件序列状态

        Args:
            chat_id: 聊天ID

        Returns:
            EventSequenceStatus对象
        """
        events = self.events.get(chat_id, [])

        # 获取各类事件
        recent_events = self.get_recent_events(chat_id, 10)
        upcoming_events = self.get_upcoming_events(chat_id, 30, 5)
        milestone_events = self.get_milestone_events(chat_id)
        recurring_events = self.get_recurring_events(chat_id)

        # 统计本周/本月事件
        now = time.time()
        week_ago = now - (7 * 86400)
        month_ago = now - (30 * 86400)

        events_this_week = len([e for e in events if e.timestamp >= week_ago])
        events_this_month = len([e for e in events if e.timestamp >= month_ago])

        # 计算间隔和活跃期
        avg_interval = self._calculate_event_interval(events)
        most_active = self._find_most_active_period(events)

        # 下一个周期性事件
        next_recurring = upcoming_events[0] if upcoming_events and upcoming_events[0].recurrence != "none" else None

        return EventSequenceStatus(
            chat_id=chat_id,
            recent_events=recent_events,
            upcoming_events=upcoming_events,
            milestone_events=milestone_events,
            total_events=len(events),
            events_this_month=events_this_month,
            events_this_week=events_this_week,
            recurring_events=recurring_events,
            next_recurring_event=next_recurring,
            avg_event_interval_days=avg_interval,
            most_active_period=most_active,
            timestamp=time.time(),
        )
