"""
语言风格感知模块
分析用户的语言风格、常用词汇、表达习惯等
"""

import time
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from src.common.logger import get_logger

logger = get_logger("language_style_perception")


@dataclass
class LanguageStyle:
    """语言风格数据类"""

    user_id: str = ""
    user_nickname: str = ""

    # 风格分类
    formality: str = "neutral"  # "formal"(正式) | "casual"(随意) | "neutral"(中性)
    tone: str = "neutral"  # "serious"(严肃) | "humorous"(幽默) | "friendly"(友好) | "neutral"(中性)
    politeness: str = "neutral"  # "polite"(礼貌) | "casual"(随意) | "neutral"(中性)

    # 语言特征
    avg_message_length: float = 0.0  # 平均消息长度
    vocabulary_richness: float = 0.0  # 词汇丰富度 0.0-1.0
    sentence_complexity: float = 0.0  # 句子复杂度 0.0-1.0

    # 常用词汇
    frequent_words: List[str] = None  # 常用词Top10
    catchphrases: List[str] = None  # 口头禅

    # 表情和标点使用
    emoji_usage_rate: float = 0.0  # 表情使用率
    emoticon_usage_rate: float = 0.0  # 颜文字使用率
    exclamation_usage: float = 0.0  # 感叹号使用率
    question_usage: float = 0.0  # 问句使用率

    # 打字习惯
    avg_typing_speed_estimate: float = 0.0  # 估计的打字速度（字/秒）
    punctuation_usage: float = 0.0  # 标点符号使用率

    # 语言模式
    prefers_short_messages: bool = False  # 偏好短消息
    uses_internet_slang: bool = False  # 使用网络用语
    uses_dialects: bool = False  # 使用方言

    # 特殊模式
    greeting_style: str = ""  # 打招呼方式
    farewell_style: str = ""  # 告别方式

    # 时间戳
    timestamp: float = 0.0
    data_points: int = 0

    def __post_init__(self):
        if self.frequent_words is None:
            self.frequent_words = []
        if self.catchphrases is None:
            self.catchphrases = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的语言风格摘要"""
        parts = []

        # 风格描述
        formality_desc = {"formal": "正式", "casual": "随意", "neutral": "中性"}
        tone_desc = {"serious": "严肃", "humorous": "幽默", "friendly": "友好", "neutral": "中性"}

        style_str = f"{formality_desc.get(self.formality, '中性')}、{tone_desc.get(self.tone, '中性')}"
        parts.append(f"{self.user_nickname or '用户'}说话{style_str}")

        # 表情使用
        if self.emoji_usage_rate > 0.3:
            parts.append("经常使用表情")

        # 消息长度
        if self.prefers_short_messages:
            parts.append("喜欢简短表达")
        elif self.avg_message_length > 50:
            parts.append("喜欢长篇大论")

        # 口头禅
        if self.catchphrases:
            parts.append(f"口头禅：{self.catchphrases[0]}")

        return "，".join(parts)


class LanguageStylePerception:
    """语言风格感知器"""

    # 网络用语词库
    INTERNET_SLANG = {
        "hhh", "哈哈哈", "hhhh", "233", "666", "awsl", "orz", "yyds",
        "绝绝子", "emo", "破防", "内卷", "躺平", "芜湖", "栓Q",
        "u1s1", "xswl", "nsdd", "zqsg", "dbq", "yygq", "awsl",
    }

    # 礼貌用语
    POLITE_WORDS = {
        "请", "谢谢", "麻烦", "打扰", "不好意思", "抱歉", "对不起",
        "劳驾", "辛苦", "感谢", "拜托", "您", "敬请",
    }

    # 正式用语
    FORMAL_WORDS = {
        "您", "贵", "敬", "请", "谨", "恕", "致", "敬请",
        "不胜", "甚为", "恳请", "拜托", "叨扰",
    }

    # 常见打招呼方式
    GREETINGS = [
        "你好", "您好", "hi", "hello", "嗨", "哈喽", "早", "早上好",
        "中午好", "下午好", "晚上好", "晚安", "大家好",
    ]

    # 常见告别方式
    FAREWELLS = [
        "再见", "拜拜", "bye", "88", "886", "晚安", "先走了",
        "溜了", "撤了", "下线了", "睡了",
    ]

    def __init__(self, history_window: int = 30):
        """
        初始化语言风格感知器

        Args:
            history_window: 历史分析窗口（天）
        """
        self.history_window = history_window
        self.user_messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # 消息记录: {"content": str, "timestamp": float, "length": int}

        logger.info(f"语言风格感知模块初始化完成，历史窗口: {history_window}天")

    def record_message(
        self,
        user_id: str,
        message_content: str,
        timestamp: Optional[float] = None,
    ):
        """
        记录用户消息

        Args:
            user_id: 用户ID
            message_content: 消息内容
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        message_record = {
            "content": message_content,
            "timestamp": timestamp,
            "length": len(message_content),
        }

        self.user_messages[user_id].append(message_record)

        # 清理过期数据
        self._cleanup_old_messages(user_id)

    def _cleanup_old_messages(self, user_id: str):
        """清理过期消息"""
        cutoff_time = time.time() - (self.history_window * 86400)
        self.user_messages[user_id] = [
            msg for msg in self.user_messages[user_id]
            if msg["timestamp"] >= cutoff_time
        ]

    def _analyze_formality(self, messages: List[str]) -> str:
        """分析正式程度"""
        formal_count = 0
        casual_count = 0

        for msg in messages:
            # 正式用语
            formal_count += sum(1 for word in self.FORMAL_WORDS if word in msg)

            # 随意表达（表情、语气词、网络用语）
            has_emoji = bool(re.search(r'[😀-🙏]', msg))
            has_emoticon = bool(re.search(r'[（(][^)]*[）)]|[><]|[oO][_-][oO]', msg))
            has_slang = any(slang in msg for slang in self.INTERNET_SLANG)

            if has_emoji or has_emoticon or has_slang:
                casual_count += 1

        if formal_count > casual_count * 2:
            return "formal"
        elif casual_count > formal_count * 2:
            return "casual"
        else:
            return "neutral"

    def _analyze_tone(self, messages: List[str]) -> str:
        """分析语气"""
        humor_indicators = ["哈哈", "hh", "笑", "😂", "🤣", "😄", "有趣", "好玩"]
        serious_indicators = ["重要", "严肃", "认真", "必须", "务必"]
        friendly_indicators = ["嗯", "哦", "呀", "呢", "吧", "嘛", "哟", "😊", "😁"]

        humor_score = sum(
            1 for msg in messages
            for indicator in humor_indicators
            if indicator in msg
        )
        serious_score = sum(
            1 for msg in messages
            for indicator in serious_indicators
            if indicator in msg
        )
        friendly_score = sum(
            1 for msg in messages
            for indicator in friendly_indicators
            if indicator in msg
        )

        scores = {
            "humorous": humor_score,
            "serious": serious_score,
            "friendly": friendly_score,
        }

        if max(scores.values()) == 0:
            return "neutral"

        return max(scores, key=scores.get)

    def _analyze_politeness(self, messages: List[str]) -> str:
        """分析礼貌程度"""
        polite_count = sum(
            1 for msg in messages
            for word in self.POLITE_WORDS
            if word in msg
        )

        avg_polite = polite_count / len(messages) if messages else 0

        if avg_polite > 0.3:
            return "polite"
        elif avg_polite < 0.05:
            return "casual"
        else:
            return "neutral"

    def _extract_vocabulary(self, messages: List[str]) -> tuple[List[str], float]:
        """
        提取常用词汇

        Returns:
            (frequent_words, vocabulary_richness)
        """
        all_words = []
        for msg in messages:
            # 提取中文词（2-4字）
            chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', msg)
            all_words.extend(chinese_words)

        if not all_words:
            return [], 0.0

        # 停用词
        stopwords = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "这", "那", "和", "与"}
        all_words = [w for w in all_words if w not in stopwords]

        # 词频统计
        word_freq = Counter(all_words)
        frequent_words = [word for word, count in word_freq.most_common(10)]

        # 词汇丰富度
        vocabulary_richness = len(set(all_words)) / len(all_words) if all_words else 0.0

        return frequent_words, vocabulary_richness

    def _detect_catchphrases(self, messages: List[str]) -> List[str]:
        """检测口头禅"""
        # 简单检测：高频短语
        phrases = []
        for msg in messages:
            # 提取2-5字的短语
            chinese_phrases = re.findall(r'[\u4e00-\u9fa5]{2,5}', msg)
            phrases.extend(chinese_phrases)

        phrase_freq = Counter(phrases)
        # 至少出现3次才算口头禅
        catchphrases = [
            phrase for phrase, count in phrase_freq.most_common(5)
            if count >= 3
        ]

        return catchphrases

    def _calculate_emoji_usage(self, messages: List[str]) -> tuple[float, float]:
        """
        计算表情使用率

        Returns:
            (emoji_rate, emoticon_rate)
        """
        emoji_count = sum(1 for msg in messages if re.search(r'[😀-🙏]', msg))
        emoticon_count = sum(
            1 for msg in messages
            if re.search(r'[（(][^)]*[）)]|[><]|[oO][_-][oO]|qwq|owo|uwu', msg, re.IGNORECASE)
        )

        emoji_rate = emoji_count / len(messages) if messages else 0.0
        emoticon_rate = emoticon_count / len(messages) if messages else 0.0

        return emoji_rate, emoticon_rate

    def _calculate_punctuation_usage(self, messages: List[str]) -> tuple[float, float]:
        """
        计算标点使用率

        Returns:
            (exclamation_rate, question_rate)
        """
        exclamation_count = sum(1 for msg in messages if '!' in msg or '！' in msg)
        question_count = sum(1 for msg in messages if '?' in msg or '？' in msg)

        exclamation_rate = exclamation_count / len(messages) if messages else 0.0
        question_rate = question_count / len(messages) if messages else 0.0

        return exclamation_rate, question_rate

    def _detect_greeting_style(self, messages: List[str]) -> str:
        """检测打招呼方式"""
        for msg in messages:
            msg_lower = msg.lower()
            for greeting in self.GREETINGS:
                if greeting in msg_lower:
                    return greeting
        return ""

    def _detect_farewell_style(self, messages: List[str]) -> str:
        """检测告别方式"""
        # 检查最后几条消息
        recent_messages = messages[-10:]
        for msg in recent_messages:
            msg_lower = msg.lower()
            for farewell in self.FAREWELLS:
                if farewell in msg_lower:
                    return farewell
        return ""

    def get_language_style(self, user_id: str, user_nickname: str = "") -> LanguageStyle:
        """
        获取用户语言风格

        Args:
            user_id: 用户ID
            user_nickname: 用户昵称

        Returns:
            LanguageStyle对象
        """
        message_records = self.user_messages.get(user_id, [])

        if not message_records:
            return LanguageStyle(
                user_id=user_id,
                user_nickname=user_nickname,
                timestamp=time.time(),
                data_points=0,
            )

        messages = [record["content"] for record in message_records]
        message_lengths = [record["length"] for record in message_records]

        # 分析风格
        formality = self._analyze_formality(messages)
        tone = self._analyze_tone(messages)
        politeness = self._analyze_politeness(messages)

        # 语言特征
        avg_length = sum(message_lengths) / len(message_lengths)
        frequent_words, vocab_richness = self._extract_vocabulary(messages)
        catchphrases = self._detect_catchphrases(messages)

        # 句子复杂度（简化：基于平均长度和标点数量）
        avg_punctuation = sum(msg.count('，') + msg.count('。') + msg.count(',') + msg.count('.') for msg in messages) / len(messages)
        sentence_complexity = min(1.0, (avg_length / 50 + avg_punctuation / 3) / 2)

        # 表情和标点
        emoji_rate, emoticon_rate = self._calculate_emoji_usage(messages)
        exclamation_rate, question_rate = self._calculate_punctuation_usage(messages)

        # 打字速度估计（如果有时间戳可以计算）
        typing_speed = 0.0  # TODO: 需要更精确的时间戳

        # 标点使用率
        punct_chars = sum(
            msg.count('，') + msg.count('。') + msg.count('！') + msg.count('？') +
            msg.count(',') + msg.count('.') + msg.count('!') + msg.count('?')
            for msg in messages
        )
        total_chars = sum(len(msg) for msg in messages)
        punctuation_usage = punct_chars / total_chars if total_chars > 0 else 0.0

        # 语言模式
        prefers_short = avg_length < 15
        uses_slang = any(slang in msg for msg in messages for slang in self.INTERNET_SLANG)

        # 检测方言（简化：检测特定方言词汇）
        dialect_words = {"嘞", "咧", "嘛", "撒", "哈", "嗦", "嘎", "哦豁"}
        uses_dialects = sum(1 for msg in messages for word in dialect_words if word in msg) > len(messages) * 0.1

        # 打招呼和告别方式
        greeting_style = self._detect_greeting_style(messages)
        farewell_style = self._detect_farewell_style(messages)

        return LanguageStyle(
            user_id=user_id,
            user_nickname=user_nickname,
            formality=formality,
            tone=tone,
            politeness=politeness,
            avg_message_length=avg_length,
            vocabulary_richness=vocab_richness,
            sentence_complexity=sentence_complexity,
            frequent_words=frequent_words,
            catchphrases=catchphrases,
            emoji_usage_rate=emoji_rate,
            emoticon_usage_rate=emoticon_rate,
            exclamation_usage=exclamation_rate,
            question_usage=question_rate,
            avg_typing_speed_estimate=typing_speed,
            punctuation_usage=punctuation_usage,
            prefers_short_messages=prefers_short,
            uses_internet_slang=uses_slang,
            uses_dialects=uses_dialects,
            greeting_style=greeting_style,
            farewell_style=farewell_style,
            timestamp=time.time(),
            data_points=len(message_records),
        )
