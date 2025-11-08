"""
麦麦感知模块

全方位的感知系统，让麦麦能够感知：
- 设备运行状况（CPU、内存、磁盘、GPU、网络）
- 环境信息（时间、天气、节日）
- 用户状态（活跃度、情绪、意图）
- 会话上下文（话题、氛围、节奏）
- 自身状态（情绪、能量、记忆负载）
"""

from .perception_manager import perception_manager

__all__ = ["perception_manager"]
__version__ = "1.0.0"
