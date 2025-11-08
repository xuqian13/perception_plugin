"""
麦麦感知插件

全方位的感知系统，包含：

基础感知：
- 设备运行状况感知（CPU、内存、磁盘、GPU、网络）
- 环境感知（时间、天气、节日）
- 用户状态感知（活跃度、情绪、意图）
- 会话上下文感知（话题、氛围、节奏）
- 自我状态感知（情绪、能量、记忆）

高级感知：
- 行为模式感知（作息习惯、活跃时段、话题偏好）
- 社交网络感知（群组角色、影响力分析、小团体检测）
- 语言风格感知（正式/随意、幽默/严肃、口头禅）
- 事件序列感知（生日、纪念日、里程碑事件）
- 安全感知（敏感内容、垃圾信息、风险评估）
- 插件系统感知（插件状态监控、健康度评估、启用/禁用管理）
"""

import asyncio
from typing import List, Tuple, Type, Optional, Dict, Any

from src.plugin_system import (
    BaseEventHandler,
    EventType,
    MaiMessages,
    CustomEventHandlerResult,
    BasePlugin,
    BaseTool,
    register_plugin,
    ComponentInfo,
    ToolInfo,
    EventHandlerInfo,
)
from src.plugin_system.base.config_types import ConfigField
from src.llm_models.payload_content.tool_option import ToolParamType
from src.common.logger import get_logger

from .perception_manager import perception_manager

logger = get_logger("perception_plugin")


# ===== 事件处理器 =====

class PerceptionMessageHandler(BaseEventHandler):
    """感知消息处理器 - 记录消息用于感知分析"""

    event_type = EventType.ON_MESSAGE
    handler_name = "perception_message_handler"
    handler_description = "记录消息用于感知分析"
    weight = 5
    intercept_message = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 加载配置
        self.enabled = self.get_config("plugin.enabled", True)

        if self.enabled:
            # 配置感知管理器
            config = {
                "enabled_modules": {
                    # 基础模块
                    "device": self.get_config("perception.device.enabled", True),
                    "environment": self.get_config("perception.environment.enabled", False),
                    "user": self.get_config("perception.user.enabled", True),
                    "context": self.get_config("perception.context.enabled", True),
                    "self": self.get_config("perception.self.enabled", True),
                    # 高级模块
                    "behavior_pattern": self.get_config("perception.behavior_pattern.enabled", True),
                    "social_network": self.get_config("perception.social_network.enabled", True),
                    "language_style": self.get_config("perception.language_style.enabled", True),
                    "event_sequence": self.get_config("perception.event_sequence.enabled", True),
                    "security": self.get_config("perception.security.enabled", True),
                    "plugin_status": self.get_config("perception.plugin_status.enabled", True),
                },
                "environment": {
                    "enable_weather": self.get_config("perception.environment.enable_weather", False),
                    "weather_api_key": self.get_config("perception.environment.weather_api_key", ""),
                    "location": self.get_config("perception.environment.location", ""),
                },
                "behavior_pattern": {
                    "history_days": self.get_config("perception.behavior_pattern.history_days", 30),
                },
                "social_network": {
                    "interaction_threshold_days": self.get_config("perception.social_network.interaction_threshold_days", 7),
                },
                "language_style": {
                    "history_window": self.get_config("perception.language_style.history_window", 30),
                },
                "event_sequence": {
                    "auto_detect": self.get_config("perception.event_sequence.auto_detect", True),
                },
                "security": {
                    "sensitivity": self.get_config("perception.security.sensitivity", "medium"),
                },
                "cache_ttl": self.get_config("perception.cache_ttl", 60),
            }
            perception_manager.configure(config)

            logger.info("感知消息处理器已初始化")

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """处理消息事件"""
        if not self.enabled or not message:
            return True, True, None, None, None

        try:
            # 提取消息信息
            chat_id = message.stream_id
            user_id = message.message_base_info.get("user_id", "")
            user_nickname = message.message_base_info.get("user_name", "")
            message_content = message.plain_text

            if chat_id and user_id and message_content:
                # 异步记录到感知管理器，避免阻塞消息处理
                asyncio.create_task(
                    self._async_record_message(
                        chat_id=chat_id,
                        user_id=user_id,
                        message_content=message_content,
                        user_nickname=user_nickname,
                    )
                )

            return True, True, None, None, None

        except Exception as e:
            logger.error(f"感知消息处理失败: {e}", exc_info=True)
            return True, True, None, None, None

    async def _async_record_message(
        self, chat_id: str, user_id: str, message_content: str, user_nickname: str
    ):
        """异步记录消息（不阻塞主流程）"""
        try:
            # 在后台任务中记录消息
            perception_manager.record_user_message(
                chat_id=chat_id,
                user_id=user_id,
                message_content=message_content,
                user_nickname=user_nickname,
            )
        except Exception as e:
            logger.error(f"异步记录消息失败: {e}", exc_info=True)


class PerceptionLLMHandler(BaseEventHandler):
    """感知LLM调用处理器 - 记录LLM调用并注入日程状态"""

    event_type = EventType.POST_LLM
    handler_name = "perception_llm_handler"
    handler_description = "记录LLM调用并注入当前日程状态到prompt"
    weight = 5
    intercept_message = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enabled = self.get_config("plugin.enabled", True)
        self.inject_schedule = self.get_config("perception.self.inject_schedule", True)

    async def execute(
        self, message: MaiMessages | None
    ) -> Tuple[bool, bool, Optional[str], Optional[CustomEventHandlerResult], Optional[MaiMessages]]:
        """处理LLM事件"""
        if not self.enabled or not message:
            return True, True, None, None, None

        try:
            # 记录LLM调用
            perception_manager.record_llm_call(1)

            # 记录消息处理
            perception_manager.record_message_processed(1)

            # 注入日程信息到prompt
            if self.inject_schedule and message.llm_prompt:
                try:
                    # 获取chat_id
                    chat_id = message.stream_id if hasattr(message, 'stream_id') else None

                    if chat_id:
                        # 获取感知快照
                        snapshot = await perception_manager.get_perception_snapshot(chat_id=chat_id)

                        if snapshot and snapshot.self_status:
                            self_status = snapshot.self_status

                            # 构建日程提示
                            schedule_prompt = ""
                            if self_status.current_activity:
                                # 使用更自然、符合麦麦风格的提示语气
                                schedule_prompt = f"\n【当前状态】\n"
                                schedule_prompt += f"这会儿正{self_status.current_activity}"

                                if self_status.current_activity_description:
                                    schedule_prompt += f"（{self_status.current_activity_description}）"

                                schedule_prompt += f"\n回复时可以自然提到当前在做什么，不要刻意强调。"

                                if self_status.next_activity and self_status.next_activity_time:
                                    schedule_prompt += f"\n等下{self_status.next_activity_time}要{self_status.next_activity}。"

                                schedule_prompt += "\n"

                            # 如果有日程信息，注入到prompt
                            if schedule_prompt:
                                original_prompt = str(message.llm_prompt)
                                # 在prompt开头注入日程信息，使用更显眼的格式
                                new_prompt = schedule_prompt + "\n" + original_prompt
                                message.modify_llm_prompt(new_prompt, suppress_warning=True)
                                logger.debug(f"已注入日程状态: {schedule_prompt.strip()}")

                except Exception as e:
                    logger.debug(f"注入日程信息失败: {e}")

            return True, True, None, None, message

        except Exception as e:
            logger.error(f"感知LLM处理失败: {e}", exc_info=True)
            return True, True, None, None, None


# ===== 工具 =====

class GetPerceptionTool(BaseTool):
    """获取感知状态工具"""

    name = "get_perception"
    description = "获取麦麦的全方位感知状态，包括设备、环境、用户、会话上下文和自我状态"
    parameters = [
        ("include_device", ToolParamType.BOOLEAN, "是否包含设备状态", False, None),
        ("include_environment", ToolParamType.BOOLEAN, "是否包含环境状态", False, None),
        ("include_context", ToolParamType.BOOLEAN, "是否包含会话上下文", False, None),
        ("include_self", ToolParamType.BOOLEAN, "是否包含自我状态", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            # 获取参数
            include_device = function_args.get("include_device", True)
            include_environment = function_args.get("include_environment", False)
            include_context = function_args.get("include_context", True)
            include_self = function_args.get("include_self", True)

            # 获取消息信息（从上下文中获取）
            # TODO: 从工具调用上下文获取chat_id
            chat_id = None

            # 获取感知快照
            snapshot = await perception_manager.get_perception_snapshot(chat_id=chat_id)

            # 构建响应
            parts = []

            if include_environment and snapshot.environment:
                parts.append(f"【环境感知】\n{snapshot.environment.get_human_readable_summary()}")

            if include_device and snapshot.device:
                parts.append(f"【设备状态】\n{snapshot.device.get_human_readable_summary()}")

            if include_context and snapshot.context:
                parts.append(f"【会话上下文】\n{snapshot.context.get_human_readable_summary()}")

            if include_self and snapshot.self_status:
                parts.append(f"【自我状态】\n{snapshot.self_status.get_human_readable_summary()}")

            content = "\n\n".join(parts) if parts else "感知数据获取中..."

            return {"type": "perception", "id": "perception_snapshot", "content": content}

        except Exception as e:
            logger.error(f"获取感知状态失败: {e}", exc_info=True)
            return {"type": "error", "id": "perception", "content": f"获取感知状态失败: {str(e)}"}


class GetDeviceStatusTool(BaseTool):
    """获取设备状态工具"""

    name = "get_device_status"
    description = "获取设备运行状况，包括CPU、内存、磁盘、GPU等"
    parameters = [
        ("detailed", ToolParamType.BOOLEAN, "是否显示详细信息", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            device_status = await perception_manager.get_device_status()

            if not device_status:
                return {"type": "error", "id": "device_status", "content": "设备状态获取失败"}

            content = f"""设备运行状况：
CPU使用率: {device_status.cpu_percent:.1f}%
内存使用率: {device_status.memory_percent:.1f}%
磁盘使用率: {device_status.disk_percent:.1f}%
系统负载: {device_status.load_avg_1min:.2f} / {device_status.load_avg_5min:.2f} / {device_status.load_avg_15min:.2f}
状态评估: {device_status.get_status_level()}
{f'GPU使用率: {device_status.gpu_percent:.1f}%' if device_status.gpu_available else ''}
{f'GPU显存使用: {device_status.gpu_memory_percent:.1f}%' if device_status.gpu_available else ''}"""

            return {"type": "device_status", "id": "device", "content": content}

        except Exception as e:
            logger.error(f"获取设备状态失败: {e}", exc_info=True)
            return {"type": "error", "id": "device_status", "content": f"获取设备状态失败: {str(e)}"}


class GetContextStatusTool(BaseTool):
    """获取会话上下文状态工具"""

    name = "get_context_status"
    description = "获取当前会话的上下文信息，包括话题、氛围、对话节奏等"
    parameters = [
        ("detailed", ToolParamType.BOOLEAN, "是否显示详细信息", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            # TODO: 从工具调用上下文获取chat_id
            chat_id = None

            if not chat_id:
                return {"type": "error", "id": "context_status", "content": "无法获取会话ID"}

            context_status = perception_manager.get_context_status(chat_id)

            if not context_status:
                return {"type": "error", "id": "context_status", "content": "会话上下文获取失败"}

            topics_str = "、".join(context_status.current_topics) if context_status.current_topics else "暂无"

            content = f"""会话上下文状态：
气氛: {context_status.atmosphere}（分数: {context_status.atmosphere_score:.1f}/10）
对话节奏: {context_status.conversation_pace}
活跃用户数（5分钟）: {context_status.active_user_count_5min}
消息数（5分钟）: {context_status.message_count_5min}
当前话题: {topics_str}
话题连贯性: {context_status.topic_coherence:.2f}
互动模式: {context_status.interaction_pattern}"""

            return {"type": "context_status", "id": "context", "content": content}

        except Exception as e:
            logger.error(f"获取会话上下文失败: {e}", exc_info=True)
            return {"type": "error", "id": "context_status", "content": f"获取会话上下文失败: {str(e)}"}


# ===== 性能监控工具 =====

class GetPerceptionStatsTool(BaseTool):
    """获取感知模块性能统计工具"""

    name = "get_perception_stats"
    description = "获取感知模块的性能统计信息，包括缓存命中率、消息处理量、批量处理统计等"
    parameters = [
        ("format", ToolParamType.STRING, "输出格式: simple(简洁)/detailed(详细)", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            stats = perception_manager.get_stats()

            content = f"""【感知模块性能统计】

📊 消息处理:
  收到消息: {stats['total_messages_received']}
  已处理: {stats['total_messages_processed']}
  批量刷新次数: {stats['batch_flush_count']}
  当前缓冲区: {stats['buffer_size']}/{stats['buffer_threshold']}

💾 缓存性能:
  缓存命中: {stats['cache_hits']}
  缓存未命中: {stats['cache_misses']}
  命中率: {stats['cache_hit_rate']}
  当前缓存数: {stats['cache_size']}/{stats['cache_max_size']}

💡 提示:
  - 命中率高表示缓存策略有效
  - 缓冲区满时会自动批量处理
  - 缓存满时使用LRU策略淘汰旧数据"""

            return {"type": "perception_stats", "id": "stats", "content": content}

        except Exception as e:
            logger.error(f"获取性能统计失败: {e}", exc_info=True)
            return {"type": "error", "id": "perception_stats", "content": f"获取性能统计失败: {str(e)}"}


class GetPerceptionMonitorTool(BaseTool):
    """获取感知模块可视化监控工具"""

    name = "get_perception_monitor"
    description = "获取感知模块的可视化性能监控，包括趋势图表、健康度评分和优化建议"
    parameters = [
        ("show_charts", ToolParamType.BOOLEAN, "是否显示图表", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            # 获取基础统计
            stats = perception_manager.get_stats()

            # 获取可视化数据
            viz_data = perception_manager.get_visualization_data()
            health = viz_data["health_score"]

            # 构建监控报告
            content_parts = []

            # 1. 健康度总览
            content_parts.append(f"""╔════════════════════════════════════════════╗
║     🎯 麦麦感知模块 - 性能监控仪表盘     ║
╚════════════════════════════════════════════╝

{health['emoji']} 系统健康度: {health['score']}/100 ({health['level']})
""")

            # 2. 实时指标
            pending = stats['total_messages_received'] - stats['total_messages_processed']
            content_parts.append(f"""
📊 实时性能指标:
┌────────────────────────────────────────┐
│ 消息处理                               │
│  ├─ 收到: {stats['total_messages_received']} 条                  │
│  ├─ 已处理: {stats['total_messages_processed']} 条                │
│  ├─ 积压: {pending} 条                      │
│  └─ 批量刷新: {stats['batch_flush_count']} 次              │
│                                        │
│ 缓存性能                               │
│  ├─ 命中率: {stats['cache_hit_rate']}               │
│  ├─ 命中: {stats['cache_hits']}                      │
│  ├─ 未命中: {stats['cache_misses']}                    │
│  └─ 当前缓存: {stats['cache_size']}/{stats['cache_max_size']}                │
│                                        │
│ 批处理状态                             │
│  └─ 当前缓冲: {stats['buffer_size']}/{stats['buffer_threshold']}                  │
└────────────────────────────────────────┘
""")

            # 3. 趋势图表
            content_parts.append(f"""
📈 性能趋势分析 (最近{viz_data['data_points']}分钟):

{viz_data['cache_hit_rate_chart']}

{viz_data['messages_rate_chart']}

{viz_data['cache_size_chart']}
""")

            # 4. 问题和建议
            if health['issues'] or health['recommendations']:
                content_parts.append("\n⚠️  诊断信息:\n")

                if health['issues']:
                    content_parts.append("发现的问题:")
                    for i, issue in enumerate(health['issues'], 1):
                        content_parts.append(f"  {i}. {issue}")
                    content_parts.append("")

                if health['recommendations']:
                    content_parts.append("优化建议:")
                    for i, rec in enumerate(health['recommendations'], 1):
                        content_parts.append(f"  {i}. {rec}")
            else:
                content_parts.append("\n✅ 系统运行正常，暂无优化建议\n")

            content = "\n".join(content_parts)

            return {"type": "perception_monitor", "id": "monitor", "content": content}

        except Exception as e:
            logger.error(f"获取可视化监控失败: {e}", exc_info=True)
            return {"type": "error", "id": "perception_monitor", "content": f"获取可视化监控失败: {str(e)}"}


# ===== 插件管理工具 =====

class GetPluginSystemStatusTool(BaseTool):
    """获取插件系统状态工具"""

    name = "get_plugin_system_status"
    description = "获取整个插件系统的状态，包括已加载、已启用、失败的插件统计信息"
    parameters = [
        ("show_details", ToolParamType.BOOLEAN, "是否显示详细信息", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            plugin_system = perception_manager.get_plugin_system_status()

            if not plugin_system:
                return {"type": "error", "id": "plugin_system", "content": "插件系统状态获取失败"}

            enabled_plugins_str = "、".join(plugin_system.enabled_plugin_names) if plugin_system.enabled_plugin_names else "无"
            failed_plugins_str = "、".join(plugin_system.failed_plugin_names) if plugin_system.failed_plugin_names else "无"

            # 构建完整的插件列表（显示ID和显示名称的映射）
            plugin_list_parts = []
            if plugin_system.all_plugins:
                plugin_list_parts.append("\n所有插件列表（插件ID -> 显示名称）：")
                for p in sorted(plugin_system.all_plugins, key=lambda x: x.plugin_name):
                    status_icon = "✅" if p.is_enabled else "⛔"
                    plugin_list_parts.append(f"  {status_icon} {p.plugin_name} -> {p.display_name}")

            plugin_list_str = "\n".join(plugin_list_parts) if plugin_list_parts else ""

            content = f"""插件系统状态：
总插件数: {plugin_system.total_plugins}
已启用: {plugin_system.enabled_plugins}
已加载: {plugin_system.loaded_plugins}
加载失败: {plugin_system.failed_plugins}

总组件数: {plugin_system.total_components}
已启用组件: {plugin_system.enabled_components}

系统健康度: {plugin_system.health_score:.1f}/100
健康等级: {plugin_system.system_health}

已启用插件: {enabled_plugins_str}
失败插件: {failed_plugins_str}{plugin_list_str}

💡 提示：使用 get_plugin_info 或 get_plugin_usage 时，请使用插件ID（如 'diary_plugin'）而非显示名称（如 '日记插件'）"""

            return {"type": "plugin_system_status", "id": "plugin_system", "content": content}

        except Exception as e:
            logger.error(f"获取插件系统状态失败: {e}", exc_info=True)
            return {"type": "error", "id": "plugin_system", "content": f"获取插件系统状态失败: {str(e)}"}


class GetPluginInfoTool(BaseTool):
    """获取单个插件状态信息工具（精简版，仅状态）"""

    name = "get_plugin_info"
    description = "快速查看插件的运行状态、组件统计和依赖信息（不包含详细使用说明，如需使用说明请用get_plugin_usage）"
    parameters = [
        ("plugin_name", ToolParamType.STRING, "插件ID（如: diary_plugin, perception_plugin等，不是显示名称）", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            plugin_name = function_args.get("plugin_name")
            if not plugin_name:
                return {"type": "error", "id": "plugin_info", "content": "插件名称不能为空"}

            plugin_info = perception_manager.get_plugin_info(plugin_name)

            if not plugin_info:
                error_msg = f"插件 {plugin_name} 不存在\n\n💡 提示：\n"
                error_msg += "1. 请使用插件ID而非显示名称（如使用 'diary_plugin' 而非 '日记插件'）\n"
                error_msg += "2. 可以先使用 get_plugin_system_status 工具查看所有可用的插件ID"
                return {"type": "error", "id": "plugin_info", "content": error_msg}

            dependencies_str = "、".join(plugin_info.dependencies) if plugin_info.dependencies else "无"
            python_deps_str = "、".join(plugin_info.python_dependencies) if plugin_info.python_dependencies else "无"

            # 精简版：去掉基本信息（version/author/description），只保留状态信息
            content = f"""【{plugin_info.display_name}】状态信息：

运行状态:
  {'✅ 已启用' if plugin_info.is_enabled else '⛔ 已禁用'}
  {'✅ 已加载' if plugin_info.is_loaded else '❌ 未加载'}
  {'❌ 错误: ' + plugin_info.error_message if plugin_info.has_error else '✅ 运行正常'}

组件统计:
  总数: {plugin_info.total_components}
  已启用: {plugin_info.enabled_components}

依赖信息:
  插件依赖: {dependencies_str}
  Python依赖: {python_deps_str}
  类型: {'内置插件' if plugin_info.is_built_in else '外部插件'}

💡 提示: 如需查看详细使用说明，请使用 get_plugin_usage 工具"""

            return {"type": "plugin_info", "id": plugin_name, "content": content}

        except Exception as e:
            logger.error(f"获取插件信息失败: {e}", exc_info=True)
            return {"type": "error", "id": "plugin_info", "content": f"获取插件信息失败: {str(e)}"}


class EnablePluginTool(BaseTool):
    """启用插件工具"""

    name = "enable_plugin"
    description = "启用指定的插件"
    parameters = [
        ("plugin_name", ToolParamType.STRING, "插件名称", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            plugin_name = function_args.get("plugin_name")
            if not plugin_name:
                return {"type": "error", "id": "enable_plugin", "content": "插件名称不能为空"}

            success = await perception_manager.enable_plugin(plugin_name)

            if success:
                content = f"✅ 插件 {plugin_name} 已成功启用"
                return {"type": "enable_plugin", "id": plugin_name, "content": content}
            else:
                content = f"❌ 插件 {plugin_name} 启用失败"
                return {"type": "error", "id": "enable_plugin", "content": content}

        except Exception as e:
            logger.error(f"启用插件失败: {e}", exc_info=True)
            return {"type": "error", "id": "enable_plugin", "content": f"启用插件失败: {str(e)}"}


class DisablePluginTool(BaseTool):
    """禁用插件工具"""

    name = "disable_plugin"
    description = "禁用指定的插件"
    parameters = [
        ("plugin_name", ToolParamType.STRING, "插件名称", True, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            plugin_name = function_args.get("plugin_name")
            if not plugin_name:
                return {"type": "error", "id": "disable_plugin", "content": "插件名称不能为空"}

            success = await perception_manager.disable_plugin(plugin_name)

            if success:
                content = f"⛔ 插件 {plugin_name} 已成功禁用"
                return {"type": "disable_plugin", "id": plugin_name, "content": content}
            else:
                content = f"❌ 插件 {plugin_name} 禁用失败"
                return {"type": "error", "id": "disable_plugin", "content": content}

        except Exception as e:
            logger.error(f"禁用插件失败: {e}", exc_info=True)
            return {"type": "error", "id": "disable_plugin", "content": f"禁用插件失败: {str(e)}"}


class GetPluginUsageTool(BaseTool):
    """获取插件使用说明工具"""

    name = "get_plugin_usage"
    description = "获取指定插件的详细使用说明、命令列表、工具和配置信息"
    parameters = [
        ("plugin_name", ToolParamType.STRING, "插件ID（如: diary_plugin, perception_plugin等，不是显示名称）", True, None),
        ("include_readme", ToolParamType.BOOLEAN, "是否包含完整README文档", False, None),
    ]
    available_for_llm = True

    async def execute(self, function_args: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        try:
            plugin_name = function_args.get("plugin_name")
            if not plugin_name:
                return {"type": "error", "id": "plugin_usage", "content": "插件名称不能为空"}

            include_readme = function_args.get("include_readme", False)

            usage_info = perception_manager.get_plugin_usage(plugin_name)

            if not usage_info:
                return {"type": "error", "id": "plugin_usage", "content": f"获取插件 {plugin_name} 的使用说明失败"}

            if "error" in usage_info:
                # 优化错误提示，提供帮助信息
                error_msg = usage_info["error"]
                if "不存在" in error_msg:
                    error_msg += "\n\n💡 提示：\n"
                    error_msg += "1. 请使用插件ID而非显示名称（如使用 'diary_plugin' 而非 '日记插件'）\n"
                    error_msg += "2. 可以先使用 get_plugin_system_status 工具查看所有可用的插件ID"
                return {"type": "error", "id": "plugin_usage", "content": error_msg}

            # 构建使用说明文本
            parts = []

            # 基本信息
            parts.append(f"# {usage_info['display_name']} ({usage_info['plugin_name']})")
            parts.append(f"版本: {usage_info['version']}")
            parts.append(f"作者: {usage_info['author']}")
            parts.append(f"描述: {usage_info['description']}")
            parts.append("")

            # 命令列表
            if usage_info["commands"]:
                parts.append("## 命令 (Commands)")
                for cmd in usage_info["commands"]:
                    status = "✅" if cmd["enabled"] else "⛔"
                    parts.append(f"- {status} `{cmd['name']}`: {cmd['description']}")
                parts.append("")

            # 工具列表
            if usage_info["tools"]:
                parts.append("## 工具 (Tools)")
                for tool in usage_info["tools"]:
                    status = "✅" if tool["enabled"] else "⛔"
                    parts.append(f"- {status} `{tool['name']}`: {tool['description']}")
                parts.append("")

            # 事件处理器列表
            if usage_info["event_handlers"]:
                parts.append("## 事件处理器 (Event Handlers)")
                for handler in usage_info["event_handlers"]:
                    status = "✅" if handler["enabled"] else "⛔"
                    parts.append(f"- {status} `{handler['name']}`: {handler['description']}")
                parts.append("")

            # README（如果请求且存在）
            if include_readme and usage_info["readme"]:
                parts.append("## 详细文档 (README)")
                parts.append("")
                parts.append(usage_info["readme"])
            elif usage_info["readme"]:
                parts.append("💡 提示: 使用 `include_readme=true` 参数可以查看完整的README文档")

            content = "\n".join(parts)

            return {"type": "plugin_usage", "id": plugin_name, "content": content}

        except Exception as e:
            logger.error(f"获取插件使用说明失败: {e}", exc_info=True)
            return {"type": "error", "id": "plugin_usage", "content": f"获取插件使用说明失败: {str(e)}"}


# ===== 插件注册 =====

@register_plugin
class PerceptionPlugin(BasePlugin):
    """麦麦感知插件"""

    plugin_name = "perception_plugin"
    plugin_description = "全方位的感知系统，包含设备、环境、用户、会话、自我等基础感知，以及行为模式、社交网络、语言风格、事件序列、安全、插件系统等高级感知"
    plugin_version = "1.0.0"
    plugin_author = "MaiBot Community"
    enable_plugin = True
    config_file_name = "config.toml"
    dependencies = []
    python_dependencies = ["psutil"]

    # 配置Schema
    config_schema: dict = {
        "plugin": {
            "enabled": ConfigField(type=bool, default=True, description="是否启用插件"),
        },
        "perception": {
            "device": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用设备感知"),
            },
            "environment": {
                "enabled": ConfigField(type=bool, default=False, description="是否启用环境感知"),
                "enable_weather": ConfigField(type=bool, default=False, description="是否启用天气感知"),
                "weather_api_key": ConfigField(type=str, default="", description="天气API密钥"),
                "location": ConfigField(type=str, default="", description="位置信息"),
            },
            "user": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用用户状态感知"),
            },
            "context": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用会话上下文感知"),
            },
            "self": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用自我状态感知"),
            },
            # 高级感知模块
            "behavior_pattern": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用行为模式感知"),
                "history_days": ConfigField(type=int, default=30, description="历史分析天数"),
            },
            "social_network": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用社交网络感知"),
                "interaction_threshold_days": ConfigField(type=int, default=7, description="互动统计时间窗口（天）"),
            },
            "language_style": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用语言风格感知"),
                "history_window": ConfigField(type=int, default=30, description="历史分析窗口（天）"),
            },
            "event_sequence": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用事件序列感知"),
                "auto_detect": ConfigField(type=bool, default=True, description="是否自动检测事件"),
            },
            "security": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用安全感知"),
                "sensitivity": ConfigField(type=str, default="medium", description="敏感度级别：low/medium/high"),
            },
            "plugin_status": {
                "enabled": ConfigField(type=bool, default=True, description="是否启用插件状态感知"),
            },
            "cache_ttl": ConfigField(type=int, default=60, description="缓存有效期（秒）"),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        """返回插件组件列表"""
        return [
            # 事件处理器
            (PerceptionMessageHandler.get_handler_info(), PerceptionMessageHandler),
            (PerceptionLLMHandler.get_handler_info(), PerceptionLLMHandler),
            # 基础感知工具
            (GetPerceptionTool.get_tool_info(), GetPerceptionTool),
            (GetDeviceStatusTool.get_tool_info(), GetDeviceStatusTool),
            (GetContextStatusTool.get_tool_info(), GetContextStatusTool),
            # 性能监控工具
            (GetPerceptionStatsTool.get_tool_info(), GetPerceptionStatsTool),
            (GetPerceptionMonitorTool.get_tool_info(), GetPerceptionMonitorTool),
            # 插件管理工具（只读模式 - 仅查询功能）
            (GetPluginSystemStatusTool.get_tool_info(), GetPluginSystemStatusTool),
            (GetPluginInfoTool.get_tool_info(), GetPluginInfoTool),
            (GetPluginUsageTool.get_tool_info(), GetPluginUsageTool),
            # 禁用修改类工具以防止权限绕过（安全优化）
            # (EnablePluginTool.get_tool_info(), EnablePluginTool),
            # (DisablePluginTool.get_tool_info(), DisablePluginTool),
        ]
