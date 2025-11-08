"""
自我状态感知模块
感知麦麦自身的情绪、能量、记忆负载等状态
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from src.common.logger import get_logger

logger = get_logger("self_perception")


@dataclass
class SelfStatus:
    """自我状态数据类"""

    # 情绪相关（从mood_manager获取）
    current_mood: str = "感觉很平静"
    mood_valence: float = 0.0  # 情绪效价 (-1.0 到 1.0)
    mood_arousal: float = 0.0  # 情绪唤醒度 (0.0 到 1.0)

    # 能量相关
    energy_level: float = 100.0  # 能量等级 (0-100)
    energy_status: str = "充沛"  # "充沛" | "正常" | "疲惫" | "极度疲惫"
    fatigue_factor: float = 0.0  # 疲劳因子 (0.0-1.0)

    # 工作负载
    message_processed_1h: int = 0  # 最近1小时处理的消息数
    message_processed_24h: int = 0  # 最近24小时处理的消息数
    llm_calls_1h: int = 0  # 最近1小时的LLM调用次数
    llm_calls_24h: int = 0  # 最近24小时的LLM调用次数
    workload_level: str = "轻松"  # "轻松" | "正常" | "繁忙" | "超负荷"

    # 记忆负载
    active_conversations: int = 0  # 活跃会话数
    memory_items_count: int = 0  # 记忆项数量
    memory_usage_percent: float = 0.0  # 记忆使用率

    # 运行时间
    uptime_seconds: float = 0.0  # 运行时长（秒）
    last_restart_time: float = 0.0  # 上次重启时间

    # 自我评估
    overall_status: str = "正常"  # "优秀" | "良好" | "正常" | "需要休息"
    status_description: str = ""

    # 当前活动/日程
    current_activity: Optional[str] = None  # 当前正在做什么，例如"上课"、"吃午饭"、"娱乐时间"
    current_activity_description: Optional[str] = None  # 活动描述
    next_activity: Optional[str] = None  # 下一个活动
    next_activity_time: Optional[str] = None  # 下一个活动时间

    # 时间戳
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的自我状态摘要"""
        parts = []

        # 当前活动（优先显示）
        if self.current_activity:
            parts.append(f"正在{self.current_activity}")

        # 情绪
        parts.append(f"心情：{self.current_mood}")

        # 能量
        parts.append(f"精力{self.energy_status}")

        # 工作负载
        parts.append(f"工作负载{self.workload_level}")

        # 总体状态
        parts.append(f"状态{self.overall_status}")

        return "，".join(parts)


class SelfPerception:
    """自我状态感知器"""

    def __init__(self, start_time: Optional[float] = None):
        """
        初始化自我感知器

        Args:
            start_time: 启动时间，默认为当前时间
        """
        self.start_time = start_time if start_time else time.time()
        self.last_restart_time = self.start_time

        # 工作记录
        self.message_history = []  # (timestamp, message_count)
        self.llm_call_history = []  # (timestamp, call_count)

        # 初始能量
        self.base_energy = 100.0
        self.energy_decay_rate = 0.5  # 每小时衰减率

        # 日程缓存（减少数据库查询）
        self._schedule_cache = None
        self._schedule_cache_time = 0
        self._schedule_cache_ttl = 60  # 缓存60秒

        logger.info("自我状态感知模块初始化完成")

    def record_message_processed(self, count: int = 1, timestamp: Optional[float] = None):
        """
        记录处理的消息数

        Args:
            count: 消息数量
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        self.message_history.append((timestamp, count))

        # 清理旧数据（保留24小时）
        cutoff = timestamp - 86400
        self.message_history = [(t, c) for t, c in self.message_history if t >= cutoff]

    def record_llm_call(self, count: int = 1, timestamp: Optional[float] = None):
        """
        记录LLM调用次数

        Args:
            count: 调用次数
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        self.llm_call_history.append((timestamp, count))

        # 清理旧数据（保留24小时）
        cutoff = timestamp - 86400
        self.llm_call_history = [(t, c) for t, c in self.llm_call_history if t >= cutoff]

    def _get_count_in_window(self, history: list, time_window: float) -> int:
        """
        获取时间窗口内的计数

        Args:
            history: 历史记录
            time_window: 时间窗口（秒）

        Returns:
            总计数
        """
        current_time = time.time()
        cutoff = current_time - time_window

        return sum(count for timestamp, count in history if timestamp >= cutoff)

    def _calculate_energy_level(self, uptime_hours: float, workload_factor: float) -> tuple[float, float, str]:
        """
        计算能量等级

        Args:
            uptime_hours: 运行时长（小时）
            workload_factor: 工作负载因子 (0.0-1.0)

        Returns:
            (能量等级, 疲劳因子, 能量状态)
        """
        # 基础能量随时间衰减
        energy = self.base_energy - (uptime_hours * self.energy_decay_rate)

        # 工作负载增加疲劳
        fatigue = uptime_hours * 0.01 + workload_factor * 0.5

        # 能量受疲劳影响
        energy = max(0, energy - (fatigue * 50))

        # 能量状态
        if energy >= 80:
            status = "充沛"
        elif energy >= 50:
            status = "正常"
        elif energy >= 20:
            status = "疲惫"
        else:
            status = "极度疲惫"

        return energy, min(1.0, fatigue), status

    def _calculate_workload_level(self, msg_1h: int, llm_1h: int) -> tuple[str, float]:
        """
        计算工作负载等级

        Args:
            msg_1h: 1小时内处理的消息数
            llm_1h: 1小时内的LLM调用次数

        Returns:
            (负载等级, 负载因子)
        """
        # 综合评估
        workload_score = msg_1h * 0.1 + llm_1h * 0.5

        if workload_score >= 50:
            return "超负荷", 1.0
        elif workload_score >= 20:
            return "繁忙", 0.7
        elif workload_score >= 5:
            return "正常", 0.4
        else:
            return "轻松", 0.1

    def _analyze_mood_from_manager(self, chat_id: Optional[str] = None) -> tuple[str, float, float]:
        """
        从mood_manager获取情绪状态

        Args:
            chat_id: 聊天ID，如果为None则使用全局情绪

        Returns:
            (情绪描述, 效价, 唤醒度)
        """
        try:
            from src.mood.mood_manager import mood_manager

            if chat_id and hasattr(mood_manager, 'get_mood_by_chat_id'):
                chat_mood = mood_manager.get_mood_by_chat_id(chat_id)
                if chat_mood:
                    mood_text = chat_mood.mood_state
                    # TODO: 可以使用emotion_analyzer转换为valence/arousal
                    return mood_text, 0.0, 0.0

            # 默认情绪
            return "感觉很平静", 0.0, 0.5
        except Exception as e:
            logger.warning(f"获取情绪状态失败: {e}")
            return "感觉很平静", 0.0, 0.5

    def _evaluate_overall_status(
        self, energy_level: float, workload_level: str, fatigue_factor: float
    ) -> tuple[str, str]:
        """
        评估整体状态

        Args:
            energy_level: 能量等级
            workload_level: 工作负载等级
            fatigue_factor: 疲劳因子

        Returns:
            (状态等级, 状态描述)
        """
        # 综合评分
        score = energy_level / 100 * 0.4

        if workload_level == "轻松":
            score += 0.3
        elif workload_level == "正常":
            score += 0.2
        elif workload_level == "繁忙":
            score += 0.1

        score -= fatigue_factor * 0.3

        # 状态评级
        if score >= 0.8:
            status = "优秀"
            desc = "精力充沛，工作状态极佳"
        elif score >= 0.6:
            status = "良好"
            desc = "状态良好，运行正常"
        elif score >= 0.4:
            status = "正常"
            desc = "状态正常，可以继续工作"
        else:
            status = "需要休息"
            desc = "感觉有些疲惫，需要适当休息"

        return status, desc

    def _get_current_schedule(self, chat_id: Optional[str] = None) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        获取当前日程信息（带缓存）

        Args:
            chat_id: 聊天ID

        Returns:
            (当前活动, 活动描述, 下一个活动, 下一个活动时间)
        """
        # 检查缓存是否有效
        current_time = time.time()
        if self._schedule_cache and (current_time - self._schedule_cache_time < self._schedule_cache_ttl):
            return self._schedule_cache

        # 缓存过期，重新查询
        try:
            from plugins.autonomous_planning_plugin.planner.goal_manager import get_goal_manager
            from datetime import datetime

            goal_manager = get_goal_manager()

            # 先尝试获取全局日程（chat_id="global"）
            goals = goal_manager.get_active_goals(chat_id="global")

            # 如果没有全局日程，再尝试获取当前聊天的日程
            if not goals and chat_id:
                goals = goal_manager.get_active_goals(chat_id=chat_id)

            if not goals:
                result = (None, None, None, None)
                self._schedule_cache = result
                self._schedule_cache_time = current_time
                return result

            # 获取当前时间
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_time_minutes = current_hour * 60 + current_minute

            # 找到有时间窗口的目标
            scheduled_goals = []
            for goal in goals:
                # 向后兼容：优先从parameters读取time_window，其次从conditions读取
                time_window = None
                if goal.parameters and "time_window" in goal.parameters:
                    time_window = goal.parameters.get("time_window")
                elif goal.conditions:
                    time_window = goal.conditions.get("time_window")

                if time_window:
                    scheduled_goals.append((goal, time_window))

            if not scheduled_goals:
                result = (None, None, None, None)
                self._schedule_cache = result
                self._schedule_cache_time = current_time
                return result

            # 排序：按开始时间
            scheduled_goals.sort(key=lambda x: x[1][0] * 60)

            # 查找当前活动
            current_activity = None
            current_description = None
            for goal, (start_hour, end_hour) in scheduled_goals:
                start_minutes = start_hour * 60
                end_minutes = end_hour * 60
                if start_minutes <= current_time_minutes < end_minutes:
                    current_activity = goal.name
                    current_description = goal.description
                    break

            # 查找下一个活动
            next_activity = None
            next_time = None
            for goal, (start_hour, end_hour) in scheduled_goals:
                start_minutes = start_hour * 60
                if start_minutes > current_time_minutes:
                    next_activity = goal.name
                    next_time = f"{start_hour:02d}:{0:02d}"
                    break

            result = (current_activity, current_description, next_activity, next_time)
            self._schedule_cache = result
            self._schedule_cache_time = current_time
            return result

        except Exception as e:
            logger.debug(f"获取日程信息失败: {e}")
            result = (None, None, None, None)
            self._schedule_cache = result
            self._schedule_cache_time = current_time
            return result

    def get_self_status(
        self,
        chat_id: Optional[str] = None,
        active_conversations: int = 0,
        memory_items_count: int = 0,
    ) -> SelfStatus:
        """
        获取自我状态

        Args:
            chat_id: 当前聊天ID（用于获取情绪）
            active_conversations: 活跃会话数
            memory_items_count: 记忆项数量

        Returns:
            SelfStatus对象
        """
        current_time = time.time()

        # 运行时长
        uptime_seconds = current_time - self.start_time
        uptime_hours = uptime_seconds / 3600

        # 工作负载统计
        msg_1h = self._get_count_in_window(self.message_history, 3600)
        msg_24h = self._get_count_in_window(self.message_history, 86400)
        llm_1h = self._get_count_in_window(self.llm_call_history, 3600)
        llm_24h = self._get_count_in_window(self.llm_call_history, 86400)

        # 计算工作负载
        workload_level, workload_factor = self._calculate_workload_level(msg_1h, llm_1h)

        # 计算能量等级
        energy_level, fatigue_factor, energy_status = self._calculate_energy_level(uptime_hours, workload_factor)

        # 获取情绪状态
        current_mood, mood_valence, mood_arousal = self._analyze_mood_from_manager(chat_id)

        # 记忆使用率（简化计算）
        max_memory_items = 10000  # 假设最大记忆项
        memory_usage_percent = min(100.0, (memory_items_count / max_memory_items) * 100)

        # 评估整体状态
        overall_status, status_description = self._evaluate_overall_status(
            energy_level, workload_level, fatigue_factor
        )

        # 获取当前日程
        current_activity, current_activity_description, next_activity, next_activity_time = self._get_current_schedule(chat_id)

        return SelfStatus(
            current_mood=current_mood,
            mood_valence=mood_valence,
            mood_arousal=mood_arousal,
            energy_level=energy_level,
            energy_status=energy_status,
            fatigue_factor=fatigue_factor,
            message_processed_1h=msg_1h,
            message_processed_24h=msg_24h,
            llm_calls_1h=llm_1h,
            llm_calls_24h=llm_24h,
            workload_level=workload_level,
            active_conversations=active_conversations,
            memory_items_count=memory_items_count,
            memory_usage_percent=memory_usage_percent,
            uptime_seconds=uptime_seconds,
            last_restart_time=self.last_restart_time,
            overall_status=overall_status,
            status_description=status_description,
            current_activity=current_activity,
            current_activity_description=current_activity_description,
            next_activity=next_activity,
            next_activity_time=next_activity_time,
            timestamp=current_time,
        )

    def reset_energy(self):
        """重置能量（休息后）"""
        self.base_energy = 100.0
        self.last_restart_time = time.time()
        logger.info("能量已重置")
