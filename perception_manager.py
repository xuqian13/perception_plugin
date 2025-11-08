"""
感知管理器
统一管理和调度所有感知子模块
"""

import time
import asyncio
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import OrderedDict, deque

from src.common.logger import get_logger
from .core import (
    DevicePerception,
    DeviceStatus,
    EnvironmentPerception,
    EnvironmentStatus,
    UserPerception,
    UserStatus,
    ContextPerception,
    ContextStatus,
    SelfPerception,
    SelfStatus,
    BehaviorPatternPerception,
    BehaviorPattern,
    SocialNetworkPerception,
    SocialNetworkStatus,
    LanguageStylePerception,
    LanguageStyle,
    EventSequencePerception,
    EventSequenceStatus,
    SecurityPerception,
    SecurityStatus,
    PluginStatusPerception,
    PluginSystemStatus,
    PluginStatusInfo,
)

logger = get_logger("perception_manager")


@dataclass
class PerceptionSnapshot:
    """感知快照 - 包含所有维度的感知数据"""

    # 基础感知
    # 设备状态
    device: Optional[DeviceStatus] = None

    # 环境状态
    environment: Optional[EnvironmentStatus] = None

    # 用户状态
    users: Dict[str, UserStatus] = None

    # 会话上下文
    context: Optional[ContextStatus] = None

    # 自我状态
    self_status: Optional[SelfStatus] = None

    # 高级感知
    # 行为模式
    behavior_patterns: Dict[str, BehaviorPattern] = None

    # 社交网络
    social_network: Optional[SocialNetworkStatus] = None

    # 语言风格
    language_styles: Dict[str, LanguageStyle] = None

    # 事件序列
    event_sequence: Optional[EventSequenceStatus] = None

    # 安全状态
    security_status: Optional[SecurityStatus] = None

    # 插件系统状态
    plugin_system: Optional[PluginSystemStatus] = None

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.users is None:
            self.users = {}
        if self.behavior_patterns is None:
            self.behavior_patterns = {}
        if self.language_styles is None:
            self.language_styles = {}
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            # 基础感知
            "device": self.device.to_dict() if self.device else None,
            "environment": self.environment.to_dict() if self.environment else None,
            "users": {uid: status.to_dict() for uid, status in self.users.items()},
            "context": self.context.to_dict() if self.context else None,
            "self_status": self.self_status.to_dict() if self.self_status else None,
            # 高级感知
            "behavior_patterns": {uid: pattern.to_dict() for uid, pattern in self.behavior_patterns.items()},
            "social_network": self.social_network.to_dict() if self.social_network else None,
            "language_styles": {uid: style.to_dict() for uid, style in self.language_styles.items()},
            "event_sequence": self.event_sequence.to_dict() if self.event_sequence else None,
            "security_status": self.security_status.to_dict() if self.security_status else None,
            "plugin_system": self.plugin_system.to_dict() if self.plugin_system else None,
            "timestamp": self.timestamp,
        }
        return result

    def get_comprehensive_summary(self) -> str:
        """获取全面的感知摘要"""
        parts = []

        # 基础感知
        # 环境
        if self.environment:
            parts.append(f"[环境] {self.environment.get_human_readable_summary()}")

        # 设备
        if self.device:
            parts.append(f"[设备] {self.device.get_human_readable_summary()}")

        # 会话上下文
        if self.context:
            parts.append(f"[会话] {self.context.get_human_readable_summary()}")

        # 自我状态
        if self.self_status:
            parts.append(f"[自我] {self.self_status.get_human_readable_summary()}")

        # 用户状态（最多展示3个）
        if self.users:
            user_summaries = []
            for user_id, user_status in list(self.users.items())[:3]:
                user_summaries.append(f"{user_status.get_human_readable_summary()}")
            if user_summaries:
                parts.append(f"[用户] {'; '.join(user_summaries)}")

        # 高级感知
        # 社交网络
        if self.social_network:
            parts.append(f"[社交] {self.social_network.get_human_readable_summary()}")

        # 事件序列
        if self.event_sequence:
            parts.append(f"[事件] {self.event_sequence.get_human_readable_summary()}")

        # 安全状态
        if self.security_status and self.security_status.risk_level != "safe":
            parts.append(f"[安全] {self.security_status.get_human_readable_summary()}")

        # 插件系统
        if self.plugin_system:
            parts.append(f"[插件] {self.plugin_system.get_human_readable_summary()}")

        return "\n".join(parts)


class PerceptionManager:
    """
    感知管理器

    统一管理和调度所有感知子模块，提供以下功能：
    1. 实时感知数据收集
    2. 感知数据缓存和查询
    3. 感知事件触发
    4. 感知数据持久化（可选）
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 初始化基础子模块
        self.device_perception = DevicePerception()
        self.environment_perception = None  # 延迟初始化
        self.user_perception = UserPerception()
        self.context_perception = ContextPerception()
        self.self_perception = SelfPerception()

        # 初始化高级子模块
        self.behavior_perception = None  # 延迟初始化
        self.social_network_perception = None  # 延迟初始化
        self.language_perception = None  # 延迟初始化
        self.event_perception = None  # 延迟初始化
        self.security_perception = None  # 延迟初始化
        self.plugin_status_perception = PluginStatusPerception()  # 立即初始化

        # 缓存优化（LRU缓存）
        self.perception_cache: OrderedDict[str, PerceptionSnapshot] = OrderedDict()
        self.cache_ttl: float = 60.0  # 缓存有效期（秒）
        self.cache_max_size: int = 100  # 最大缓存数量（LRU淘汰）

        # 批量处理和防抖
        self.message_buffer: deque = deque(maxlen=50)  # 消息缓冲区
        self.buffer_size_threshold: int = 10  # 缓冲区大小阈值
        self.flush_interval: float = 2.0  # 刷新间隔（秒）
        self.last_flush_time: float = time.time()
        self._flush_task: Optional[asyncio.Task] = None

        # 性能监控统计
        self.stats = {
            "total_messages_received": 0,
            "total_messages_processed": 0,
            "batch_flush_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # 历史性能数据（用于可视化）
        self.history_max_points = 60  # 保存最近60个数据点
        self.history_data = {
            "timestamps": deque(maxlen=self.history_max_points),
            "cache_hit_rates": deque(maxlen=self.history_max_points),
            "buffer_sizes": deque(maxlen=self.history_max_points),
            "cache_sizes": deque(maxlen=self.history_max_points),
            "messages_per_minute": deque(maxlen=self.history_max_points),
        }
        self.last_history_record_time = time.time()
        self.last_message_count_for_rate = 0

        # 配置
        self.enabled_modules = {
            # 基础模块
            "device": True,
            "environment": False,  # 默认关闭天气
            "user": True,
            "context": True,
            "self": True,
            # 高级模块
            "behavior_pattern": True,
            "social_network": True,
            "language_style": True,
            "event_sequence": True,
            "security": True,
            "plugin_status": True,
        }

        logger.info("感知管理器初始化完成")

        # 启动定期刷新任务
        self._start_auto_flush()

    def configure(self, config: Dict[str, Any]):
        """
        配置感知管理器

        Args:
            config: 配置字典，包含各模块的配置
        """
        # 启用/禁用模块
        if "enabled_modules" in config:
            self.enabled_modules.update(config["enabled_modules"])

        # 环境感知配置
        if "environment" in config and self.enabled_modules.get("environment"):
            env_config = config["environment"]
            self.environment_perception = EnvironmentPerception(
                enable_weather=env_config.get("enable_weather", False),
                weather_api_key=env_config.get("weather_api_key"),
                location=env_config.get("location", ""),
            )

        # 行为模式感知配置
        if "behavior_pattern" in config and self.enabled_modules.get("behavior_pattern"):
            bp_config = config["behavior_pattern"]
            self.behavior_perception = BehaviorPatternPerception(
                history_days=bp_config.get("history_days", 30)
            )

        # 社交网络感知配置
        if "social_network" in config and self.enabled_modules.get("social_network"):
            self.social_network_perception = SocialNetworkPerception(
                interaction_threshold_days=config["social_network"].get("interaction_threshold_days", 7)
            )

        # 语言风格感知配置
        if "language_style" in config and self.enabled_modules.get("language_style"):
            self.language_perception = LanguageStylePerception(
                history_window=config["language_style"].get("history_window", 30)
            )

        # 事件序列感知配置
        if "event_sequence" in config and self.enabled_modules.get("event_sequence"):
            self.event_perception = EventSequencePerception(
                auto_detect=config["event_sequence"].get("auto_detect", True)
            )

        # 安全感知配置
        if "security" in config and self.enabled_modules.get("security"):
            self.security_perception = SecurityPerception(
                sensitivity=config["security"].get("sensitivity", "medium")
            )

        # 缓存配置
        if "cache_ttl" in config:
            self.cache_ttl = config["cache_ttl"]

        logger.info(f"感知管理器配置完成，启用模块: {self.enabled_modules}")

    def _start_auto_flush(self):
        """启动自动刷新任务"""
        try:
            loop = asyncio.get_event_loop()
            if not self._flush_task or self._flush_task.done():
                self._flush_task = loop.create_task(self._auto_flush_loop())
                logger.debug("自动刷新任务已启动")
        except RuntimeError:
            # 没有事件循环时跳过
            logger.debug("未检测到事件循环，跳过自动刷新任务")

    async def _auto_flush_loop(self):
        """自动刷新循环"""
        tune_counter = 0

        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                current_time = time.time()

                # 检查是否需要刷新
                if (current_time - self.last_flush_time >= self.flush_interval
                    and len(self.message_buffer) > 0):
                    self._flush_message_buffer()

                # 每30次循环执行一次自动调优（约1分钟）
                tune_counter += 1
                if tune_counter >= 30:
                    self.auto_tune()
                    self._record_history_data()  # 记录历史数据
                    tune_counter = 0

            except asyncio.CancelledError:
                logger.debug("自动刷新任务被取消")
                break
            except Exception as e:
                logger.error(f"自动刷新任务出错: {e}", exc_info=True)
                await asyncio.sleep(5)  # 出错后等待5秒再继续

    def _flush_message_buffer(self):
        """刷新消息缓冲区（批量处理）"""
        if not self.message_buffer:
            return

        batch_size = len(self.message_buffer)
        logger.debug(f"批量处理 {batch_size} 条消息")

        # 批量处理所有缓冲的消息
        while self.message_buffer:
            msg_data = self.message_buffer.popleft()
            self._process_single_message(msg_data)
            self.stats["total_messages_processed"] += 1

        self.last_flush_time = time.time()
        self.stats["batch_flush_count"] += 1

        logger.debug(f"批量处理完成，已处理 {batch_size} 条消息")

    def _process_single_message(self, msg_data: Dict[str, Any]):
        """处理单条消息"""
        chat_id = msg_data["chat_id"]
        user_id = msg_data["user_id"]
        message_content = msg_data["message_content"]
        user_nickname = msg_data["user_nickname"]
        timestamp = msg_data["timestamp"]

        # 基础模块
        if self.enabled_modules.get("user"):
            self.user_perception.record_user_activity(user_id, message_content, timestamp)

        if self.enabled_modules.get("context"):
            self.context_perception.record_message(
                chat_id, user_id, message_content, user_nickname, timestamp
            )

        # 高级模块
        if self.enabled_modules.get("behavior_pattern") and self.behavior_perception:
            self.behavior_perception.record_message(user_id, message_content, chat_id, timestamp)

        if self.enabled_modules.get("social_network") and self.social_network_perception:
            self.social_network_perception.record_interaction(chat_id, user_id, None, "message", timestamp)

        if self.enabled_modules.get("language_style") and self.language_perception:
            self.language_perception.record_message(user_id, message_content, timestamp)

        if self.enabled_modules.get("event_sequence") and self.event_perception:
            if self.event_perception.auto_detect:
                self.event_perception.auto_detect_event(chat_id, message_content, user_id, timestamp)

        # 智能缓存失效
        self._invalidate_related_cache(chat_id, user_id)

    def _invalidate_related_cache(self, chat_id: str, user_id: str):
        """
        智能缓存失效 - 细粒度清除相关的缓存条目（性能优化版）

        优化策略：
        1. 只失效包含特定用户的快照缓存
        2. 不失效不包含该用户的其他快照
        3. 使用精确匹配而非模糊匹配

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
        """
        keys_to_remove = []

        # 遍历缓存，精确匹配需要失效的条目
        for key in list(self.perception_cache.keys()):
            # 解析缓存key格式: "{chat_id}_{user_ids}"
            parts = key.split('_', 1)
            if len(parts) != 2:
                continue

            key_chat_id = parts[0]
            key_user_ids = parts[1]

            # 只有满足以下条件才失效:
            # 1. chat_id匹配
            # 2. user_ids包含当前用户或为'all'
            should_invalidate = False

            if key_chat_id == chat_id:
                if key_user_ids == 'all':
                    # 'all'缓存在有新消息时总是失效
                    should_invalidate = True
                elif user_id in key_user_ids.split(','):
                    # 精确匹配用户ID（避免'123'匹配'1234'的问题）
                    user_list = key_user_ids.split(',')
                    if user_id in user_list:
                        should_invalidate = True

            if should_invalidate:
                keys_to_remove.append(key)

        # 批量删除（减少字典操作次数）
        for key in keys_to_remove:
            del self.perception_cache[key]

        # 记录统计信息
        if keys_to_remove:
            logger.debug(f"缓存失效: 清除 {len(keys_to_remove)} 个缓存项 (chat_id={chat_id}, user_id={user_id})")
            self.stats.setdefault("cache_invalidations", 0)
            self.stats["cache_invalidations"] += len(keys_to_remove)

    def record_user_message(
        self,
        chat_id: str,
        user_id: str,
        message_content: str,
        user_nickname: str = "",
        timestamp: Optional[float] = None,
    ):
        """
        记录用户消息（批量处理版本）

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            message_content: 消息内容
            user_nickname: 用户昵称
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        self.stats["total_messages_received"] += 1

        # 添加到缓冲区
        msg_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "message_content": message_content,
            "user_nickname": user_nickname,
            "timestamp": timestamp,
        }
        self.message_buffer.append(msg_data)

        # 达到阈值时立即刷新
        if len(self.message_buffer) >= self.buffer_size_threshold:
            self._flush_message_buffer()

    def record_message_processed(self, count: int = 1):
        """记录处理的消息数"""
        if self.enabled_modules.get("self"):
            self.self_perception.record_message_processed(count)

    def record_llm_call(self, count: int = 1):
        """记录LLM调用"""
        if self.enabled_modules.get("self"):
            self.self_perception.record_llm_call(count)

    async def get_device_status(self) -> Optional[DeviceStatus]:
        """获取设备状态"""
        if not self.enabled_modules.get("device"):
            return None

        try:
            return self.device_perception.get_device_status()
        except Exception as e:
            logger.error(f"获取设备状态失败: {e}")
            return None

    async def get_environment_status(self) -> Optional[EnvironmentStatus]:
        """获取环境状态"""
        if not self.enabled_modules.get("environment") or not self.environment_perception:
            return None

        try:
            return await self.environment_perception.get_environment_status()
        except Exception as e:
            logger.error(f"获取环境状态失败: {e}")
            return None

    def get_user_status(self, user_id: str, user_nickname: str = "") -> Optional[UserStatus]:
        """获取用户状态"""
        if not self.enabled_modules.get("user"):
            return None

        try:
            return self.user_perception.get_user_status(user_id, user_nickname)
        except Exception as e:
            logger.error(f"获取用户状态失败: {e}")
            return None

    def get_context_status(self, chat_id: str) -> Optional[ContextStatus]:
        """获取会话上下文状态"""
        if not self.enabled_modules.get("context"):
            return None

        try:
            return self.context_perception.get_context_status(chat_id)
        except Exception as e:
            logger.error(f"获取上下文状态失败: {e}")
            return None

    def get_self_status(
        self,
        chat_id: Optional[str] = None,
        active_conversations: int = 0,
        memory_items_count: int = 0,
    ) -> Optional[SelfStatus]:
        """获取自我状态"""
        if not self.enabled_modules.get("self"):
            return None

        try:
            return self.self_perception.get_self_status(chat_id, active_conversations, memory_items_count)
        except Exception as e:
            logger.error(f"获取自我状态失败: {e}")
            return None

    # ========== 高级感知模块方法 ==========

    def get_behavior_pattern(self, user_id: str, user_nickname: str = "") -> Optional[BehaviorPattern]:
        """获取用户行为模式"""
        if not self.enabled_modules.get("behavior_pattern") or not self.behavior_perception:
            return None

        try:
            return self.behavior_perception.get_behavior_pattern(user_id, user_nickname)
        except Exception as e:
            logger.error(f"获取行为模式失败: {e}")
            return None

    def get_social_network_status(self, chat_id: str) -> Optional[SocialNetworkStatus]:
        """获取社交网络状态"""
        if not self.enabled_modules.get("social_network") or not self.social_network_perception:
            return None

        try:
            return self.social_network_perception.get_social_network_status(chat_id)
        except Exception as e:
            logger.error(f"获取社交网络状态失败: {e}")
            return None

    def get_language_style(self, user_id: str, user_nickname: str = "") -> Optional[LanguageStyle]:
        """获取用户语言风格"""
        if not self.enabled_modules.get("language_style") or not self.language_perception:
            return None

        try:
            return self.language_perception.get_language_style(user_id, user_nickname)
        except Exception as e:
            logger.error(f"获取语言风格失败: {e}")
            return None

    def get_event_sequence_status(self, chat_id: str) -> Optional[EventSequenceStatus]:
        """获取事件序列状态"""
        if not self.enabled_modules.get("event_sequence") or not self.event_perception:
            return None

        try:
            return self.event_perception.get_event_sequence_status(chat_id)
        except Exception as e:
            logger.error(f"获取事件序列状态失败: {e}")
            return None

    def analyze_message_security(
        self, chat_id: str, user_id: str, message: str, timestamp: Optional[float] = None
    ) -> Optional[SecurityStatus]:
        """分析消息安全性"""
        if not self.enabled_modules.get("security") or not self.security_perception:
            return None

        try:
            return self.security_perception.analyze_message(chat_id, user_id, message, timestamp)
        except Exception as e:
            logger.error(f"安全分析失败: {e}")
            return None

    def get_plugin_system_status(self) -> Optional[PluginSystemStatus]:
        """获取插件系统状态"""
        if not self.enabled_modules.get("plugin_status") or not self.plugin_status_perception:
            return None

        try:
            return self.plugin_status_perception.get_plugin_system_status()
        except Exception as e:
            logger.error(f"获取插件系统状态失败: {e}")
            return None

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginStatusInfo]:
        """获取单个插件信息"""
        if not self.enabled_modules.get("plugin_status") or not self.plugin_status_perception:
            return None

        try:
            return self.plugin_status_perception.get_plugin_info(plugin_name)
        except Exception as e:
            logger.error(f"获取插件信息失败: {e}")
            return None

    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if not self.enabled_modules.get("plugin_status") or not self.plugin_status_perception:
            return False

        try:
            return await self.plugin_status_perception.enable_plugin(plugin_name)
        except Exception as e:
            logger.error(f"启用插件失败: {e}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if not self.enabled_modules.get("plugin_status") or not self.plugin_status_perception:
            return False

        try:
            return await self.plugin_status_perception.disable_plugin(plugin_name)
        except Exception as e:
            logger.error(f"禁用插件失败: {e}")
            return False

    def get_plugin_usage(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取插件使用说明"""
        if not self.enabled_modules.get("plugin_status") or not self.plugin_status_perception:
            return None

        try:
            return self.plugin_status_perception.get_plugin_usage(plugin_name)
        except Exception as e:
            logger.error(f"获取插件使用说明失败: {e}")
            return None

    async def get_perception_snapshot(
        self,
        chat_id: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> PerceptionSnapshot:
        """
        获取感知快照（优化版：LRU缓存）

        Args:
            chat_id: 聊天ID
            user_ids: 需要获取状态的用户ID列表
            use_cache: 是否使用缓存

        Returns:
            完整的感知快照
        """
        cache_key = f"{chat_id}_{','.join(user_ids) if user_ids else 'all'}"

        # 检查缓存（LRU）
        if use_cache and cache_key in self.perception_cache:
            cached = self.perception_cache[cache_key]
            if time.time() - cached.timestamp < self.cache_ttl:
                # 更新LRU顺序（将访问的缓存项移到最后）
                self.perception_cache.move_to_end(cache_key)
                self.stats["cache_hits"] += 1
                logger.debug(f"缓存命中: {cache_key}")
                return cached
            else:
                # 缓存过期，删除
                del self.perception_cache[cache_key]

        self.stats["cache_misses"] += 1

        # 收集基础感知数据
        device_status = await self.get_device_status()
        environment_status = await self.get_environment_status()
        context_status = self.get_context_status(chat_id) if chat_id else None
        self_status = self.get_self_status(chat_id)

        # 收集用户状态
        users_status = {}
        if user_ids and self.enabled_modules.get("user"):
            for user_id in user_ids:
                status = self.get_user_status(user_id)
                if status:
                    users_status[user_id] = status

        # 收集高级感知数据
        # 行为模式
        behavior_patterns = {}
        if user_ids and self.enabled_modules.get("behavior_pattern"):
            for user_id in user_ids:
                pattern = self.get_behavior_pattern(user_id)
                if pattern:
                    behavior_patterns[user_id] = pattern

        # 社交网络
        social_network = self.get_social_network_status(chat_id) if chat_id else None

        # 语言风格
        language_styles = {}
        if user_ids and self.enabled_modules.get("language_style"):
            for user_id in user_ids:
                style = self.get_language_style(user_id)
                if style:
                    language_styles[user_id] = style

        # 事件序列
        event_sequence = self.get_event_sequence_status(chat_id) if chat_id else None

        # 安全状态（最后一条消息的安全分析，如果有的话）
        security_status = None
        # 注意：安全分析需要消息内容，这里不主动分析

        # 插件系统状态
        plugin_system = self.get_plugin_system_status()

        # 创建快照
        snapshot = PerceptionSnapshot(
            # 基础感知
            device=device_status,
            environment=environment_status,
            users=users_status,
            context=context_status,
            self_status=self_status,
            # 高级感知
            behavior_patterns=behavior_patterns,
            social_network=social_network,
            language_styles=language_styles,
            event_sequence=event_sequence,
            security_status=security_status,
            plugin_system=plugin_system,
            timestamp=time.time(),
        )

        # 更新缓存（LRU淘汰）
        if use_cache:
            # 检查缓存大小，超过限制则淘汰最旧的
            if len(self.perception_cache) >= self.cache_max_size:
                # 移除最早的缓存项（FIFO/LRU）
                oldest_key = next(iter(self.perception_cache))
                del self.perception_cache[oldest_key]
                logger.debug(f"缓存已满，淘汰最旧项: {oldest_key}")

            self.perception_cache[cache_key] = snapshot

        return snapshot

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        cache_hit_rate = 0.0
        total_cache_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_cache_requests > 0:
            cache_hit_rate = self.stats["cache_hits"] / total_cache_requests * 100

        return {
            **self.stats,
            "cache_size": len(self.perception_cache),
            "cache_max_size": self.cache_max_size,
            "cache_hit_rate": f"{cache_hit_rate:.2f}%",
            "buffer_size": len(self.message_buffer),
            "buffer_threshold": self.buffer_size_threshold,
        }

    def auto_tune(self):
        """自动调优（根据运行状态调整参数）"""
        try:
            # 获取统计信息
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]

            if total_requests < 100:
                # 数据不足，不调优
                return

            cache_hit_rate = self.stats["cache_hits"] / total_requests

            # 调优缓存大小
            if cache_hit_rate < 0.5:
                # 命中率低，增加缓存大小
                old_size = self.cache_max_size
                self.cache_max_size = min(200, int(self.cache_max_size * 1.2))
                if old_size != self.cache_max_size:
                    logger.info(f"自动调优：缓存大小从 {old_size} 增加到 {self.cache_max_size} (命中率: {cache_hit_rate:.2%})")

            elif cache_hit_rate > 0.9 and self.cache_max_size > 50:
                # 命中率很高且缓存较大，可以适当减小
                old_size = self.cache_max_size
                self.cache_max_size = max(50, int(self.cache_max_size * 0.9))
                if old_size != self.cache_max_size:
                    logger.info(f"自动调优：缓存大小从 {old_size} 减少到 {self.cache_max_size} (命中率: {cache_hit_rate:.2%}，节省内存)")

            # 调优批处理阈值
            avg_batch_size = self.stats["total_messages_processed"] / max(1, self.stats["batch_flush_count"])

            if avg_batch_size < 3 and self.buffer_size_threshold > 5:
                # 平均批量太小，减小阈值以更快处理
                old_threshold = self.buffer_size_threshold
                self.buffer_size_threshold = max(5, int(self.buffer_size_threshold * 0.8))
                if old_threshold != self.buffer_size_threshold:
                    logger.info(f"自动调优：批处理阈值从 {old_threshold} 减少到 {self.buffer_size_threshold} (平均批量: {avg_batch_size:.1f})")

            elif avg_batch_size > 8 and self.buffer_size_threshold < 20:
                # 平均批量较大，增加阈值以提高效率
                old_threshold = self.buffer_size_threshold
                self.buffer_size_threshold = min(20, int(self.buffer_size_threshold * 1.2))
                if old_threshold != self.buffer_size_threshold:
                    logger.info(f"自动调优：批处理阈值从 {old_threshold} 增加到 {self.buffer_size_threshold} (平均批量: {avg_batch_size:.1f})")

        except Exception as e:
            logger.error(f"自动调优失败: {e}", exc_info=True)

    def _record_history_data(self):
        """记录历史性能数据（用于趋势可视化）"""
        try:
            current_time = time.time()

            # 计算缓存命中率
            total_cache_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            cache_hit_rate = 0.0
            if total_cache_requests > 0:
                cache_hit_rate = self.stats["cache_hits"] / total_cache_requests * 100

            # 计算每分钟消息数
            time_elapsed = current_time - self.last_history_record_time
            if time_elapsed > 0:
                messages_since_last = self.stats["total_messages_received"] - self.last_message_count_for_rate
                messages_per_minute = (messages_since_last / time_elapsed) * 60
            else:
                messages_per_minute = 0

            # 记录数据点
            self.history_data["timestamps"].append(current_time)
            self.history_data["cache_hit_rates"].append(cache_hit_rate)
            self.history_data["buffer_sizes"].append(len(self.message_buffer))
            self.history_data["cache_sizes"].append(len(self.perception_cache))
            self.history_data["messages_per_minute"].append(messages_per_minute)

            # 更新记录时间
            self.last_history_record_time = current_time
            self.last_message_count_for_rate = self.stats["total_messages_received"]

        except Exception as e:
            logger.error(f"记录历史数据失败: {e}", exc_info=True)

    def _generate_ascii_chart(self, data: List[float], height: int = 8, width: int = 50, title: str = "") -> str:
        """生成ASCII字符图表"""
        if not data or len(data) == 0:
            return f"{title}\n(暂无数据)"

        # 数据归一化
        max_val = max(data) if max(data) > 0 else 1
        min_val = min(data)
        range_val = max_val - min_val if max_val > min_val else 1

        lines = []
        lines.append(f"📈 {title}")
        lines.append(f"范围: {min_val:.1f} - {max_val:.1f}")
        lines.append("")

        # 生成图表
        for i in range(height, 0, -1):
            threshold = min_val + (range_val * i / height)
            line = f"{threshold:6.1f} │"

            for val in data[-width:]:  # 只显示最近的width个点
                if val >= threshold:
                    line += "█"
                elif val >= threshold - (range_val / height / 2):
                    line += "▄"
                else:
                    line += " "

            lines.append(line)

        # X轴
        lines.append("       └" + "─" * min(len(data), width))
        lines.append(f"        最近{min(len(data), width)}个数据点")

        return "\n".join(lines)

    def get_visualization_data(self) -> Dict[str, Any]:
        """获取可视化数据"""
        cache_hit_rate_chart = self._generate_ascii_chart(
            list(self.history_data["cache_hit_rates"]),
            height=6,
            width=40,
            title="缓存命中率趋势 (%)"
        )

        messages_rate_chart = self._generate_ascii_chart(
            list(self.history_data["messages_per_minute"]),
            height=6,
            width=40,
            title="消息处理速率 (条/分钟)"
        )

        cache_size_chart = self._generate_ascii_chart(
            list(self.history_data["cache_sizes"]),
            height=6,
            width=40,
            title="缓存使用量"
        )

        # 健康度评分
        health_score = self._calculate_health_score()

        return {
            "cache_hit_rate_chart": cache_hit_rate_chart,
            "messages_rate_chart": messages_rate_chart,
            "cache_size_chart": cache_size_chart,
            "health_score": health_score,
            "data_points": len(self.history_data["timestamps"]),
        }

    def _calculate_health_score(self) -> Dict[str, Any]:
        """计算系统健康度评分"""
        score = 100.0
        issues = []
        recommendations = []

        # 评估缓存命中率
        if len(self.history_data["cache_hit_rates"]) > 0:
            avg_hit_rate = sum(self.history_data["cache_hit_rates"]) / len(self.history_data["cache_hit_rates"])

            if avg_hit_rate < 50:
                score -= 20
                issues.append("缓存命中率偏低")
                recommendations.append("建议增加缓存大小或调整缓存策略")
            elif avg_hit_rate > 90:
                recommendations.append("缓存性能优秀")

        # 评估缓冲区使用情况
        if len(self.history_data["buffer_sizes"]) > 0:
            avg_buffer = sum(self.history_data["buffer_sizes"]) / len(self.history_data["buffer_sizes"])
            buffer_usage_rate = avg_buffer / self.buffer_size_threshold

            if buffer_usage_rate > 0.9:
                score -= 15
                issues.append("缓冲区经常接近满载")
                recommendations.append("建议增加批处理阈值")

        # 评估消息处理积压
        pending = self.stats["total_messages_received"] - self.stats["total_messages_processed"]
        if pending > 100:
            score -= 25
            issues.append(f"消息处理积压: {pending}条")
            recommendations.append("建议检查处理性能或增加处理能力")
        elif pending > 50:
            score -= 10
            issues.append(f"轻微消息积压: {pending}条")

        # 健康等级
        if score >= 90:
            health_level = "优秀"
            emoji = "🟢"
        elif score >= 70:
            health_level = "良好"
            emoji = "🟡"
        elif score >= 50:
            health_level = "一般"
            emoji = "🟠"
        else:
            health_level = "需要优化"
            emoji = "🔴"

        return {
            "score": round(score, 1),
            "level": health_level,
            "emoji": emoji,
            "issues": issues,
            "recommendations": recommendations,
        }

    def clear_cache(self):
        """清除缓存"""
        self.perception_cache.clear()
        logger.info("感知缓存已清除")

    def get_perception_summary(
        self,
        chat_id: Optional[str] = None,
        user_ids: Optional[List[str]] = None,
    ) -> str:
        """
        获取感知摘要（同步版本，用于快速获取）

        Args:
            chat_id: 聊天ID
            user_ids: 用户ID列表

        Returns:
            人类可读的感知摘要
        """
        parts = []

        # 环境（如果启用）
        if self.enabled_modules.get("environment") and self.environment_perception:
            try:
                # 注意：这里使用同步方法，可能不包含最新天气
                from datetime import datetime
                now = datetime.now()
                time_period = self.environment_perception.get_time_period(now.hour)
                parts.append(f"现在是{time_period}")
            except Exception:
                pass

        # 设备
        if self.enabled_modules.get("device"):
            try:
                device = self.device_perception.get_device_status()
                if device:
                    parts.append(device.get_human_readable_summary())
            except Exception:
                pass

        # 上下文
        if chat_id and self.enabled_modules.get("context"):
            try:
                context = self.context_perception.get_context_status(chat_id)
                if context:
                    parts.append(context.get_human_readable_summary())
            except Exception:
                pass

        # 自我
        if self.enabled_modules.get("self"):
            try:
                self_status = self.self_perception.get_self_status(chat_id)
                if self_status:
                    parts.append(self_status.get_human_readable_summary())
            except Exception:
                pass

        return "；".join(parts) if parts else "感知数据获取中..."


# 全局单例
perception_manager = PerceptionManager()
