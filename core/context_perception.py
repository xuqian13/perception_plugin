"""
会话上下文感知模块
感知当前对话的话题、氛围、节奏等
"""

import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import deque
from src.common.logger import get_logger

logger = get_logger("context_perception")


@dataclass
class MessageRecord:
    """消息记录"""

    user_id: str
    content: str
    timestamp: float
    user_nickname: str = ""


@dataclass
class ContextStatus:
    """会话上下文状态数据类"""

    chat_id: str = ""

    # 活跃度相关
    message_count_5min: int = 0
    message_count_1h: int = 0
    active_user_count_5min: int = 0
    active_user_count_1h: int = 0

    # 氛围相关
    atmosphere: str = "calm"  # "lively" | "active" | "calm" | "quiet" | "silent"
    atmosphere_score: float = 0.0  # 0.0-10.0

    # 对话节奏
    conversation_pace: str = "normal"  # "fast" | "normal" | "slow" | "stopped"
    avg_message_interval: float = 0.0  # 平均消息间隔（秒）
    last_message_time: float = 0.0

    # 话题相关
    current_topics: List[str] = None  # 当前话题关键词
    topic_coherence: float = 0.5  # 话题连贯性 0.0-1.0

    # 互动模式
    interaction_pattern: str = "normal"  # "debate" | "chat" | "qa" | "normal"
    question_count: int = 0  # 最近的问题数量

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.current_topics is None:
            self.current_topics = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的上下文摘要"""
        parts = []

        # 氛围描述
        atmosphere_desc = {
            "lively": "气氛热烈",
            "active": "气氛活跃",
            "calm": "气氛平静",
            "quiet": "气氛安静",
            "silent": "无人说话",
        }
        parts.append(atmosphere_desc.get(self.atmosphere, "气氛正常"))

        # 参与人数
        if self.active_user_count_5min > 0:
            parts.append(f"{self.active_user_count_5min}人正在交流")

        # 话题
        if self.current_topics:
            topics_str = "、".join(self.current_topics[:3])
            parts.append(f"正在讨论：{topics_str}")

        return "，".join(parts)


class ContextPerception:
    """会话上下文感知器"""

    def __init__(self):
        """初始化会话上下文感知器"""
        self.chat_messages: Dict[str, deque] = {}  # chat_id -> deque of MessageRecord
        self.chat_cache: Dict[str, ContextStatus] = {}  # 上下文状态缓存

        logger.info("会话上下文感知模块初始化完成")

    def record_message(
        self,
        chat_id: str,
        user_id: str,
        content: str,
        user_nickname: str = "",
        timestamp: Optional[float] = None,
    ):
        """
        记录消息

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            content: 消息内容
            user_nickname: 用户昵称
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        message = MessageRecord(
            user_id=user_id,
            content=content,
            timestamp=timestamp,
            user_nickname=user_nickname,
        )

        if chat_id not in self.chat_messages:
            self.chat_messages[chat_id] = deque(maxlen=500)  # 最多保存500条消息

        self.chat_messages[chat_id].append(message)

        # 清理过期缓存
        if chat_id in self.chat_cache:
            cache_age = time.time() - self.chat_cache[chat_id].timestamp
            if cache_age > 60:  # 缓存1分钟
                del self.chat_cache[chat_id]

    def _get_messages_in_window(self, chat_id: str, time_window: float) -> List[MessageRecord]:
        """
        获取时间窗口内的消息

        Args:
            chat_id: 聊天ID
            time_window: 时间窗口（秒）

        Returns:
            消息列表
        """
        if chat_id not in self.chat_messages:
            return []

        current_time = time.time()
        cutoff_time = current_time - time_window

        messages = self.chat_messages[chat_id]
        return [msg for msg in messages if msg.timestamp >= cutoff_time]

    def _calculate_atmosphere(self, message_count_5min: int, active_users: int) -> tuple[str, float]:
        """
        计算气氛等级

        Args:
            message_count_5min: 5分钟内消息数
            active_users: 活跃用户数

        Returns:
            (气氛类型, 气氛分数)
        """
        # 综合消息数和活跃用户数
        activity_score = message_count_5min * 0.3 + active_users * 2.0

        if activity_score >= 15:
            return "lively", min(10.0, activity_score / 2)
        elif activity_score >= 8:
            return "active", activity_score
        elif activity_score >= 3:
            return "calm", activity_score
        elif activity_score > 0:
            return "quiet", activity_score
        else:
            return "silent", 0.0

    def _calculate_conversation_pace(self, avg_interval: float) -> str:
        """
        计算对话节奏

        Args:
            avg_interval: 平均消息间隔（秒）

        Returns:
            节奏类型
        """
        if avg_interval <= 0:
            return "stopped"
        elif avg_interval < 10:
            return "fast"
        elif avg_interval < 60:
            return "normal"
        else:
            return "slow"

    def _extract_topics(self, messages: List[MessageRecord]) -> List[str]:
        """
        提取话题关键词（简化版）

        Args:
            messages: 消息列表

        Returns:
            话题关键词列表
        """
        # TODO: 使用NLP技术进行更准确的话题提取
        # 这里使用简单的词频统计

        from collections import Counter
        import re

        # 合并所有消息
        all_text = " ".join([msg.content for msg in messages])

        # 简单分词（中文按字符，英文按单词）
        # 过滤掉常见停用词
        stopwords = {
            "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
            "这", "那", "和", "与", "及", "或", "吗", "吧", "啊", "呢",
            "a", "an", "the", "is", "are", "was", "were", "in", "on", "at",
        }

        # 提取中文词语（2-4个字）和英文单词
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', all_text)
        english_words = re.findall(r'[a-zA-Z]{3,}', all_text.lower())

        words = chinese_words + english_words
        words = [w for w in words if w not in stopwords]

        # 统计词频
        word_freq = Counter(words)

        # 返回最常见的3个词
        return [word for word, count in word_freq.most_common(5) if count >= 2]

    def _calculate_topic_coherence(self, messages: List[MessageRecord]) -> float:
        """
        计算话题连贯性

        Args:
            messages: 消息列表

        Returns:
            连贯性分数 (0.0-1.0)
        """
        if len(messages) < 2:
            return 1.0

        # 简化版：基于消息间的时间间隔和长度
        # 如果消息间隔很短且长度适中，认为连贯性较高

        total_coherence = 0.0
        for i in range(1, len(messages)):
            prev_msg = messages[i - 1]
            curr_msg = messages[i]

            time_gap = curr_msg.timestamp - prev_msg.timestamp

            # 时间间隔越短，连贯性越高
            time_coherence = max(0, 1.0 - time_gap / 300)  # 5分钟内满分

            # 消息长度合理（10-200字），连贯性较高
            length = len(curr_msg.content)
            length_coherence = 1.0 if 10 <= length <= 200 else 0.5

            total_coherence += (time_coherence + length_coherence) / 2

        return total_coherence / (len(messages) - 1)

    def _detect_interaction_pattern(self, messages: List[MessageRecord]) -> tuple[str, int]:
        """
        检测互动模式

        Args:
            messages: 消息列表

        Returns:
            (互动模式, 问题数量)
        """
        if not messages:
            return "normal", 0

        # 统计问题数量
        question_count = sum(1 for msg in messages if "?" in msg.content or "？" in msg.content)

        # 统计用户数量
        unique_users = len(set(msg.user_id for msg in messages))

        # 检测是否为辩论（多人，消息较多）
        if unique_users >= 3 and len(messages) >= 10:
            return "debate", question_count

        # 检测是否为问答模式（问题较多）
        if question_count / len(messages) > 0.4:
            return "qa", question_count

        # 检测是否为闲聊（消息较多，用户较多）
        if len(messages) >= 5 and unique_users >= 2:
            return "chat", question_count

        return "normal", question_count

    def get_context_status(self, chat_id: str) -> ContextStatus:
        """
        获取会话上下文状态

        Args:
            chat_id: 聊天ID

        Returns:
            ContextStatus对象
        """
        # 获取不同时间窗口的消息
        messages_5min = self._get_messages_in_window(chat_id, 300)
        messages_1h = self._get_messages_in_window(chat_id, 3600)

        # 统计数据
        message_count_5min = len(messages_5min)
        message_count_1h = len(messages_1h)

        active_users_5min = len(set(msg.user_id for msg in messages_5min))
        active_users_1h = len(set(msg.user_id for msg in messages_1h))

        # 计算氛围
        atmosphere, atmosphere_score = self._calculate_atmosphere(message_count_5min, active_users_5min)

        # 计算对话节奏
        avg_interval = 0.0
        last_message_time = 0.0
        if len(messages_5min) > 1:
            time_span = messages_5min[-1].timestamp - messages_5min[0].timestamp
            avg_interval = time_span / (len(messages_5min) - 1)
            last_message_time = messages_5min[-1].timestamp
        elif messages_5min:
            last_message_time = messages_5min[-1].timestamp

        conversation_pace = self._calculate_conversation_pace(avg_interval)

        # 提取话题
        current_topics = self._extract_topics(messages_1h[-20:])  # 分析最近20条消息

        # 计算话题连贯性
        topic_coherence = self._calculate_topic_coherence(messages_5min)

        # 检测互动模式
        interaction_pattern, question_count = self._detect_interaction_pattern(messages_5min)

        return ContextStatus(
            chat_id=chat_id,
            message_count_5min=message_count_5min,
            message_count_1h=message_count_1h,
            active_user_count_5min=active_users_5min,
            active_user_count_1h=active_users_1h,
            atmosphere=atmosphere,
            atmosphere_score=atmosphere_score,
            conversation_pace=conversation_pace,
            avg_message_interval=avg_interval,
            last_message_time=last_message_time,
            current_topics=current_topics,
            topic_coherence=topic_coherence,
            interaction_pattern=interaction_pattern,
            question_count=question_count,
            timestamp=time.time(),
        )
