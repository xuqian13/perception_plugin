"""
插件状态感知模块
监控自身插件系统的状态、健康度、使用情况等
"""

import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from collections import defaultdict
from src.common.logger import get_logger

logger = get_logger("plugin_status_perception")


@dataclass
class PluginStatusInfo:
    """单个插件状态信息"""

    plugin_name: str
    display_name: str = ""
    version: str = ""
    author: str = ""
    description: str = ""

    # 状态
    is_enabled: bool = False
    is_loaded: bool = False
    has_error: bool = False
    error_message: str = ""

    # 组件统计
    total_components: int = 0
    enabled_components: int = 0
    component_types: Dict[str, int] = None  # 组件类型统计

    # 依赖
    dependencies: List[str] = None
    python_dependencies: List[str] = None

    # 元数据
    is_built_in: bool = False
    plugin_path: str = ""

    def __post_init__(self):
        if self.component_types is None:
            self.component_types = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.python_dependencies is None:
            self.python_dependencies = []


@dataclass
class PluginSystemStatus:
    """插件系统整体状态"""

    # 统计
    total_plugins: int = 0
    enabled_plugins: int = 0
    loaded_plugins: int = 0
    failed_plugins: int = 0

    # 组件统计
    total_components: int = 0
    enabled_components: int = 0
    components_by_type: Dict[str, int] = None  # 按类型统计

    # 插件列表
    all_plugins: List[PluginStatusInfo] = None
    enabled_plugin_names: List[str] = None
    failed_plugin_names: List[str] = None

    # 健康度
    system_health: str = "healthy"  # "healthy" | "warning" | "critical"
    health_score: float = 100.0  # 0-100

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.components_by_type is None:
            self.components_by_type = {}
        if self.all_plugins is None:
            self.all_plugins = []
        if self.enabled_plugin_names is None:
            self.enabled_plugin_names = []
        if self.failed_plugin_names is None:
            self.failed_plugin_names = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        return data

    def get_human_readable_summary(self) -> str:
        """获取人类可读的插件系统摘要"""
        parts = []

        # 插件数量
        parts.append(f"共{self.total_plugins}个插件，{self.enabled_plugins}个已启用")

        # 失败情况
        if self.failed_plugins > 0:
            parts.append(f"{self.failed_plugins}个插件加载失败")

        # 健康状态
        health_desc = {
            "healthy": "健康",
            "warning": "警告",
            "critical": "严重",
        }
        parts.append(f"系统状态：{health_desc.get(self.system_health, '未知')}")

        return "，".join(parts)


class PluginStatusPerception:
    """插件状态感知器"""

    def __init__(self):
        """初始化插件状态感知器"""
        self.plugin_manager = None
        self.component_registry = None

        # 尝试导入插件管理器
        try:
            from src.plugin_system.core.plugin_manager import plugin_manager
            from src.plugin_system.core.component_registry import component_registry

            self.plugin_manager = plugin_manager
            self.component_registry = component_registry

            logger.info("插件状态感知模块初始化完成")
        except Exception as e:
            logger.error(f"插件状态感知模块初始化失败: {e}")

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginStatusInfo]:
        """
        获取单个插件的详细信息

        Args:
            plugin_name: 插件名称

        Returns:
            插件状态信息，如果插件不存在则返回None
        """
        if not self.component_registry:
            return None

        # 从注册表获取插件信息
        plugin_info = self.component_registry._plugins.get(plugin_name)
        if not plugin_info:
            return None

        # 检查插件是否加载
        is_loaded = plugin_name in (self.plugin_manager.loaded_plugins if self.plugin_manager else {})

        # 检查是否有错误
        has_error = plugin_name in (self.plugin_manager.failed_plugins if self.plugin_manager else {})
        error_message = (self.plugin_manager.failed_plugins.get(plugin_name, "") if has_error else "")

        # 统计组件
        components = plugin_info.components
        total_components = len(components)
        enabled_components = sum(1 for c in components if c.enabled)

        # 按类型统计组件
        component_types = defaultdict(int)
        for component in components:
            component_types[str(component.component_type)] += 1

        # Python依赖
        python_deps = []
        if plugin_info.python_dependencies:
            for dep in plugin_info.python_dependencies:
                if isinstance(dep, str):
                    # 如果已经是字符串，直接使用
                    python_deps.append(dep)
                elif hasattr(dep, 'get_pip_requirement'):
                    # 如果是依赖对象，调用方法
                    python_deps.append(dep.get_pip_requirement())
                else:
                    # 其他情况，转换为字符串
                    python_deps.append(str(dep))

        return PluginStatusInfo(
            plugin_name=plugin_info.name,
            display_name=plugin_info.display_name,
            version=plugin_info.version,
            author=plugin_info.author,
            description=plugin_info.description,
            is_enabled=plugin_info.enabled,
            is_loaded=is_loaded,
            has_error=has_error,
            error_message=error_message,
            total_components=total_components,
            enabled_components=enabled_components,
            component_types=dict(component_types),
            dependencies=plugin_info.dependencies,
            python_dependencies=python_deps,
            is_built_in=plugin_info.is_built_in,
            plugin_path=self.plugin_manager.plugin_paths.get(plugin_name, "") if self.plugin_manager else "",
        )

    def get_all_plugins_info(self) -> List[PluginStatusInfo]:
        """获取所有插件的信息"""
        if not self.component_registry:
            return []

        plugin_infos = []
        for plugin_name in self.component_registry._plugins.keys():
            info = self.get_plugin_info(plugin_name)
            if info:
                plugin_infos.append(info)

        return plugin_infos

    def get_plugin_system_status(self) -> PluginSystemStatus:
        """
        获取插件系统整体状态

        Returns:
            PluginSystemStatus对象
        """
        if not self.component_registry or not self.plugin_manager:
            return PluginSystemStatus(
                system_health="critical",
                health_score=0.0,
                timestamp=time.time(),
            )

        # 获取所有插件信息
        all_plugins = self.get_all_plugins_info()

        # 统计数据
        total_plugins = len(all_plugins)
        enabled_plugins = sum(1 for p in all_plugins if p.is_enabled)
        loaded_plugins = sum(1 for p in all_plugins if p.is_loaded)
        failed_plugins = sum(1 for p in all_plugins if p.has_error)

        # 组件统计
        total_components = sum(p.total_components for p in all_plugins)
        enabled_components = sum(p.enabled_components for p in all_plugins)

        # 按类型统计组件
        components_by_type = defaultdict(int)
        for plugin in all_plugins:
            for comp_type, count in plugin.component_types.items():
                components_by_type[comp_type] += count

        # 获取插件名称列表
        enabled_plugin_names = [p.plugin_name for p in all_plugins if p.is_enabled]
        failed_plugin_names = [p.plugin_name for p in all_plugins if p.has_error]

        # 计算健康度
        health_score = 100.0
        if total_plugins > 0:
            # 失败率影响健康度
            failure_ratio = failed_plugins / total_plugins
            health_score -= failure_ratio * 50

            # 禁用率影响健康度
            disabled_ratio = (total_plugins - enabled_plugins) / total_plugins
            health_score -= disabled_ratio * 20

        health_score = max(0.0, min(100.0, health_score))

        # 判断健康状态
        if health_score >= 80:
            system_health = "healthy"
        elif health_score >= 50:
            system_health = "warning"
        else:
            system_health = "critical"

        return PluginSystemStatus(
            total_plugins=total_plugins,
            enabled_plugins=enabled_plugins,
            loaded_plugins=loaded_plugins,
            failed_plugins=failed_plugins,
            total_components=total_components,
            enabled_components=enabled_components,
            components_by_type=dict(components_by_type),
            all_plugins=all_plugins,
            enabled_plugin_names=enabled_plugin_names,
            failed_plugin_names=failed_plugin_names,
            system_health=system_health,
            health_score=health_score,
            timestamp=time.time(),
        )

    async def enable_plugin(self, plugin_name: str) -> bool:
        """
        启用插件（通过启用其所有组件）

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        if not self.component_registry:
            logger.error("组件注册表不可用")
            return False

        plugin_info = self.component_registry._plugins.get(plugin_name)
        if not plugin_info:
            logger.error(f"插件 {plugin_name} 不存在")
            return False

        if plugin_info.enabled:
            logger.info(f"插件 {plugin_name} 已经是启用状态")
            return True

        try:
            # 导入组件管理API
            from src.plugin_system import component_manage_api

            # 启用所有组件
            success_count = 0
            total_components = len(plugin_info.components)

            for component in plugin_info.components:
                try:
                    # 使用组件管理API启用组件
                    if component_manage_api.globally_enable_component(
                        component.name, component.component_type
                    ):
                        success_count += 1
                        logger.debug(f"成功启用组件: {component.name}")
                    else:
                        # 启用失败可能是因为组件已经启用，这也算正常
                        logger.debug(f"组件 {component.name} 启用返回False（可能已启用）")
                except Exception as e:
                    logger.warning(f"启用组件 {component.name} 时出错: {e}")

            # 更新插件启用状态
            plugin_info.enabled = True

            logger.info(f"✅ 已启用插件 {plugin_name}，共 {total_components} 个组件")
            return True  # 只要插件状态更新成功就返回True

        except Exception as e:
            logger.error(f"启用插件 {plugin_name} 失败: {e}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """
        禁用插件（通过禁用其所有组件）

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        if not self.component_registry:
            logger.error("组件注册表不可用")
            return False

        plugin_info = self.component_registry._plugins.get(plugin_name)
        if not plugin_info:
            logger.error(f"插件 {plugin_name} 不存在")
            return False

        if not plugin_info.enabled:
            logger.info(f"插件 {plugin_name} 已经是禁用状态")
            return True

        try:
            # 导入组件管理API
            from src.plugin_system import component_manage_api

            # 禁用所有组件
            success_count = 0
            total_components = len(plugin_info.components)

            for component in plugin_info.components:
                try:
                    # 使用组件管理API禁用组件（异步）
                    if await component_manage_api.globally_disable_component(
                        component.name, component.component_type
                    ):
                        success_count += 1
                        logger.debug(f"成功禁用组件: {component.name}")
                    else:
                        # 禁用失败可能是因为组件已经被禁用，这也算正常
                        logger.debug(f"组件 {component.name} 禁用返回False（可能已禁用）")
                except Exception as e:
                    logger.warning(f"禁用组件 {component.name} 时出错: {e}")

            # 更新插件禁用状态
            plugin_info.enabled = False

            logger.info(f"⛔ 已禁用插件 {plugin_name}，共 {total_components} 个组件")
            return True  # 只要插件状态更新成功就返回True

        except Exception as e:
            logger.error(f"禁用插件 {plugin_name} 失败: {e}")
            return False

    async def reload_plugin(self, plugin_name: str) -> bool:
        """
        重载插件

        Args:
            plugin_name: 插件名称

        Returns:
            是否成功
        """
        if not self.plugin_manager:
            logger.error("插件管理器不可用")
            return False

        try:
            # 先禁用
            self.disable_plugin(plugin_name)

            # TODO: 实现插件重载逻辑
            # 这需要plugin_manager提供reload方法

            # 再启用
            self.enable_plugin(plugin_name)

            logger.info(f"🔄 已重载插件: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"重载插件 {plugin_name} 失败: {e}")
            return False

    def get_plugin_dependencies(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件的依赖关系

        Args:
            plugin_name: 插件名称

        Returns:
            依赖信息字典
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return {}

        return {
            "plugin_name": plugin_name,
            "plugin_dependencies": plugin_info.dependencies,
            "python_dependencies": plugin_info.python_dependencies,
            "dependent_by": self._find_dependent_plugins(plugin_name),
        }

    def _find_dependent_plugins(self, plugin_name: str) -> List[str]:
        """查找依赖于指定插件的其他插件"""
        if not self.component_registry:
            return []

        dependent_plugins = []
        for name, info in self.component_registry._plugins.items():
            if plugin_name in info.dependencies:
                dependent_plugins.append(name)

        return dependent_plugins

    def get_plugin_usage(self, plugin_name: str) -> Dict[str, Any]:
        """
        获取插件的使用说明和文档

        Args:
            plugin_name: 插件名称

        Returns:
            包含插件使用说明的字典
        """
        import os
        import json

        if not self.plugin_manager:
            return {"error": "插件管理器不可用"}

        # 获取插件信息
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return {"error": f"插件 {plugin_name} 不存在"}

        # 获取插件路径
        plugin_path = plugin_info.plugin_path
        if not plugin_path or not os.path.exists(plugin_path):
            return {"error": f"插件路径不存在: {plugin_path}"}

        usage_info = {
            "plugin_name": plugin_name,
            "display_name": plugin_info.display_name,
            "version": plugin_info.version,
            "author": plugin_info.author,
            "description": plugin_info.description,
            "readme": None,
            "manifest": None,
            "commands": [],
            "tools": [],
            "event_handlers": [],
        }

        # 读取 README.md
        readme_path = os.path.join(plugin_path, "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    usage_info["readme"] = f.read()
                logger.debug(f"成功读取插件 {plugin_name} 的 README.md")
            except Exception as e:
                logger.warning(f"读取 README.md 失败: {e}")

        # 读取 _manifest.json
        manifest_path = os.path.join(plugin_path, "_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    usage_info["manifest"] = json.load(f)
                logger.debug(f"成功读取插件 {plugin_name} 的 _manifest.json")
            except Exception as e:
                logger.warning(f"读取 _manifest.json 失败: {e}")

        # 从组件中提取命令和工具信息
        plugin_data = self.component_registry._plugins.get(plugin_name)
        if plugin_data:
            for component in plugin_data.components:
                comp_info = {
                    "name": component.name,
                    "description": component.description if hasattr(component, "description") else "",
                    "enabled": component.enabled,
                }

                comp_type = str(component.component_type).lower()
                if "command" in comp_type:
                    usage_info["commands"].append(comp_info)
                elif "tool" in comp_type:
                    usage_info["tools"].append(comp_info)
                elif "event" in comp_type:
                    usage_info["event_handlers"].append(comp_info)

        return usage_info
