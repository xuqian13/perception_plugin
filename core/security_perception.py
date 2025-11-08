"""
安全感知模块
检测敏感内容、异常行为、垃圾信息、风险评估等
"""

import time
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from src.common.logger import get_logger

logger = get_logger("security_perception")


@dataclass
class SecurityStatus:
    """安全状态数据类"""

    chat_id: str = ""
    user_id: str = ""

    # 风险评估
    risk_level: str = "safe"  # "safe" | "low" | "medium" | "high" | "critical"
    risk_score: float = 0.0  # 风险分数 0.0-100.0

    # 检测结果
    has_sensitive_content: bool = False
    has_spam: bool = False
    has_malicious_link: bool = False
    has_abnormal_behavior: bool = False

    # 详细信息
    detected_issues: List[str] = None  # 检测到的问题列表
    sensitive_keywords: List[str] = None  # 触发的敏感词
    spam_indicators: List[str] = None  # 垃圾信息指标

    # 用户行为异常
    abnormal_patterns: List[str] = None  # 异常模式
    suspicious_activity: bool = False

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.detected_issues is None:
            self.detected_issues = []
        if self.sensitive_keywords is None:
            self.sensitive_keywords = []
        if self.spam_indicators is None:
            self.spam_indicators = []
        if self.abnormal_patterns is None:
            self.abnormal_patterns = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的安全状态摘要"""
        if self.risk_level == "safe":
            return "安全状态良好"

        parts = []
        risk_desc = {
            "low": "低风险",
            "medium": "中等风险",
            "high": "高风险",
            "critical": "严重风险",
        }

        parts.append(f"安全等级：{risk_desc.get(self.risk_level, '未知')}")

        if self.detected_issues:
            parts.append(f"检测到{len(self.detected_issues)}个问题")

        return "，".join(parts)


class SecurityPerception:
    """安全感知器"""

    # 敏感词库（示例，实际应该更完善）
    SENSITIVE_KEYWORDS = {
        # 政治敏感
        "政治敏感词1", "政治敏感词2",  # 实际应该配置真实的敏感词

        # 色情暴力
        "色情词1", "暴力词1",

        # 诈骗相关
        "转账", "汇款", "中奖", "免费领取", "点击领奖",
    }

    # 垃圾信息特征
    SPAM_PATTERNS = [
        r'(加|添加).{0,5}(微信|QQ|vx)',  # 添加联系方式
        r'(免费|限时).{0,10}(领取|获得)',  # 免费领取
        r'(点击|复制).{0,10}(链接|网址)',  # 点击链接
        r'[0-9]{6,}',  # 长数字串
    ]

    # 可疑链接模式
    SUSPICIOUS_URL_PATTERNS = [
        r'bit\.ly',
        r't\.cn',
        r'短网址',
    ]

    # 欺诈指标
    FRAUD_KEYWORDS = {
        "中奖", "免费", "恭喜您", "转账", "汇款", "密码",
        "验证码", "银行卡", "身份证", "紧急", "立即",
    }

    def __init__(self, sensitivity: str = "medium"):
        """
        初始化安全感知器

        Args:
            sensitivity: 敏感度 "low" | "medium" | "high"
        """
        self.sensitivity = sensitivity

        # 用户行为历史（用于异常检测）
        # {user_id: {"message_times": [], "message_contents": []}}
        self.user_history: Dict[str, Dict[str, List]] = defaultdict(
            lambda: {"message_times": [], "message_contents": []}
        )

        # 敏感度阈值
        self.thresholds = {
            "low": {"spam_score": 80, "fraud_score": 90},
            "medium": {"spam_score": 60, "fraud_score": 70},
            "high": {"spam_score": 40, "fraud_score": 50},
        }

        logger.info(f"安全感知模块初始化完成，敏感度: {sensitivity}")

    def analyze_message(
        self,
        chat_id: str,
        user_id: str,
        message_content: str,
        timestamp: Optional[float] = None,
    ) -> SecurityStatus:
        """
        分析消息安全性

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            message_content: 消息内容
            timestamp: 时间戳

        Returns:
            SecurityStatus对象
        """
        if timestamp is None:
            timestamp = time.time()

        # 记录历史
        self.user_history[user_id]["message_times"].append(timestamp)
        self.user_history[user_id]["message_contents"].append(message_content)

        # 清理旧数据（保留7天）
        cutoff = timestamp - (7 * 86400)
        history = self.user_history[user_id]
        valid_indices = [i for i, t in enumerate(history["message_times"]) if t >= cutoff]
        history["message_times"] = [history["message_times"][i] for i in valid_indices]
        history["message_contents"] = [history["message_contents"][i] for i in valid_indices]

        # 执行各项检测
        detected_issues = []
        sensitive_keywords = []
        spam_indicators = []
        abnormal_patterns = []

        # 1. 敏感内容检测
        has_sensitive, keywords = self._detect_sensitive_content(message_content)
        if has_sensitive:
            detected_issues.append("包含敏感内容")
            sensitive_keywords = keywords

        # 2. 垃圾信息检测
        is_spam, indicators = self._detect_spam(message_content)
        if is_spam:
            detected_issues.append("疑似垃圾信息")
            spam_indicators = indicators

        # 3. 恶意链接检测
        has_malicious_link = self._detect_malicious_links(message_content)
        if has_malicious_link:
            detected_issues.append("包含可疑链接")

        # 4. 异常行为检测
        has_abnormal, patterns = self._detect_abnormal_behavior(user_id, message_content, timestamp)
        if has_abnormal:
            detected_issues.append("检测到异常行为")
            abnormal_patterns = patterns

        # 5. 欺诈检测
        fraud_score = self._detect_fraud(message_content)
        if fraud_score > self.thresholds[self.sensitivity]["fraud_score"]:
            detected_issues.append("疑似诈骗信息")

        # 计算风险分数和等级
        risk_score = self._calculate_risk_score(
            has_sensitive, is_spam, has_malicious_link, has_abnormal, fraud_score
        )
        risk_level = self._determine_risk_level(risk_score)

        return SecurityStatus(
            chat_id=chat_id,
            user_id=user_id,
            risk_level=risk_level,
            risk_score=risk_score,
            has_sensitive_content=has_sensitive,
            has_spam=is_spam,
            has_malicious_link=has_malicious_link,
            has_abnormal_behavior=has_abnormal,
            detected_issues=detected_issues,
            sensitive_keywords=sensitive_keywords,
            spam_indicators=spam_indicators,
            abnormal_patterns=abnormal_patterns,
            suspicious_activity=len(detected_issues) > 0,
            timestamp=timestamp,
        )

    def _detect_sensitive_content(self, message: str) -> tuple[bool, List[str]]:
        """检测敏感内容"""
        found_keywords = []

        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in message:
                found_keywords.append(keyword)

        return len(found_keywords) > 0, found_keywords

    def _detect_spam(self, message: str) -> tuple[bool, List[str]]:
        """检测垃圾信息"""
        indicators = []

        # 检测模式
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, message):
                indicators.append(f"匹配模式: {pattern[:20]}")

        # 检测重复字符
        if re.search(r'(.)\1{5,}', message):
            indicators.append("大量重复字符")

        # 检测全大写
        if len(message) > 10 and message.isupper():
            indicators.append("全大写文本")

        # 检测过多表情
        emoji_count = len(re.findall(r'[😀-🙏]', message))
        if emoji_count > 10:
            indicators.append("过多表情符号")

        spam_score = len(indicators) * 25  # 每个指标25分

        return spam_score > self.thresholds[self.sensitivity]["spam_score"], indicators

    def _detect_malicious_links(self, message: str) -> bool:
        """检测恶意链接"""
        # 检测URL
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message)

        for url in urls:
            for pattern in self.SUSPICIOUS_URL_PATTERNS:
                if re.search(pattern, url):
                    return True

        return False

    def _detect_abnormal_behavior(
        self, user_id: str, message: str, timestamp: float
    ) -> tuple[bool, List[str]]:
        """检测异常行为"""
        abnormal_patterns = []
        history = self.user_history[user_id]

        # 1. 短时间内大量发送
        recent_times = [t for t in history["message_times"] if timestamp - t < 60]
        if len(recent_times) > 10:
            abnormal_patterns.append("短时间内频繁发送消息")

        # 2. 重复内容
        recent_contents = history["message_contents"][-10:]
        if message in recent_contents[:-1]:  # 排除当前消息
            duplicate_count = recent_contents.count(message)
            if duplicate_count > 2:
                abnormal_patterns.append("发送重复内容")

        # 3. 消息长度异常
        if len(message) > 1000:
            abnormal_patterns.append("消息长度异常")

        # 4. 突然改变发言模式（从不发言到大量发言）
        if len(recent_times) > 5 and len(history["message_times"]) > 10:
            older_activity = len([t for t in history["message_times"] if timestamp - t > 3600])
            if older_activity < 5:  # 之前不活跃
                abnormal_patterns.append("发言模式突变")

        return len(abnormal_patterns) > 0, abnormal_patterns

    def _detect_fraud(self, message: str) -> float:
        """检测欺诈（返回分数0-100）"""
        fraud_score = 0.0

        # 检测欺诈关键词
        for keyword in self.FRAUD_KEYWORDS:
            if keyword in message:
                fraud_score += 15

        # 检测金额相关
        if re.search(r'[0-9,]+元|￥[0-9,]+|[0-9]+块钱', message):
            fraud_score += 20

        # 检测紧急性用词
        urgent_words = ["马上", "立即", "赶快", "限时", "紧急"]
        if any(word in message for word in urgent_words):
            fraud_score += 10

        return min(100.0, fraud_score)

    def _calculate_risk_score(
        self,
        has_sensitive: bool,
        is_spam: bool,
        has_malicious_link: bool,
        has_abnormal: bool,
        fraud_score: float,
    ) -> float:
        """计算综合风险分数"""
        score = 0.0

        if has_sensitive:
            score += 40
        if is_spam:
            score += 30
        if has_malicious_link:
            score += 25
        if has_abnormal:
            score += 20

        score += fraud_score * 0.5

        return min(100.0, score)

    def _determine_risk_level(self, risk_score: float) -> str:
        """判定风险等级"""
        if risk_score >= 80:
            return "critical"
        elif risk_score >= 60:
            return "high"
        elif risk_score >= 40:
            return "medium"
        elif risk_score >= 20:
            return "low"
        else:
            return "safe"

    def get_user_security_summary(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户安全摘要

        Args:
            user_id: 用户ID

        Returns:
            安全摘要字典
        """
        history = self.user_history.get(user_id, {"message_times": [], "message_contents": []})

        total_messages = len(history["message_contents"])
        if total_messages == 0:
            return {
                "user_id": user_id,
                "total_messages": 0,
                "risk_level": "safe",
                "is_trustworthy": True,
            }

        # 分析最近消息的风险
        recent_messages = history["message_contents"][-20:]
        risk_count = 0

        for msg in recent_messages:
            status = self.analyze_message("", user_id, msg)
            if status.risk_level not in ["safe", "low"]:
                risk_count += 1

        risk_ratio = risk_count / len(recent_messages)

        return {
            "user_id": user_id,
            "total_messages": total_messages,
            "risk_messages": risk_count,
            "risk_ratio": risk_ratio,
            "risk_level": "high" if risk_ratio > 0.3 else "medium" if risk_ratio > 0.1 else "safe",
            "is_trustworthy": risk_ratio < 0.1,
        }
