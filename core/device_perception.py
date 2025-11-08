"""
设备运行状况感知模块
监控系统资源使用情况：CPU、内存、磁盘、GPU、网络等

性能优化版本：
- 后台线程定期采样CPU数据，消除阻塞
- 缓存机制，减少系统调用
- 自适应采样频率
"""

import psutil
import time
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from src.common.logger import get_logger

logger = get_logger("device_perception")


@dataclass
class DeviceStatus:
    """设备状态数据类"""

    # CPU相关
    cpu_percent: float = 0.0
    cpu_count: int = 0
    cpu_freq_current: float = 0.0
    cpu_freq_max: float = 0.0

    # 内存相关
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    memory_available: int = 0

    # 磁盘相关
    disk_total: int = 0
    disk_used: int = 0
    disk_percent: float = 0.0
    disk_free: int = 0

    # 网络相关
    network_sent: int = 0
    network_recv: int = 0
    network_sent_rate: float = 0.0  # bytes/s
    network_recv_rate: float = 0.0  # bytes/s

    # GPU相关（如果可用）
    gpu_available: bool = False
    gpu_percent: float = 0.0
    gpu_memory_used: int = 0
    gpu_memory_total: int = 0
    gpu_memory_percent: float = 0.0
    gpu_temperature: float = 0.0

    # 系统负载
    load_avg_1min: float = 0.0
    load_avg_5min: float = 0.0
    load_avg_15min: float = 0.0

    # 时间戳
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_status_level(self) -> str:
        """
        获取设备状态等级

        Returns:
            "healthy" | "warning" | "critical"
        """
        # 判断关键指标
        critical_conditions = [
            self.cpu_percent > 90,
            self.memory_percent > 90,
            self.disk_percent > 95,
        ]

        warning_conditions = [
            self.cpu_percent > 70,
            self.memory_percent > 75,
            self.disk_percent > 85,
        ]

        if any(critical_conditions):
            return "critical"
        elif any(warning_conditions):
            return "warning"
        else:
            return "healthy"

    def get_human_readable_summary(self) -> str:
        """获取人类可读的状态摘要"""
        status_level = self.get_status_level()

        if status_level == "healthy":
            return f"身体状况良好，CPU使用率{self.cpu_percent:.1f}%，内存使用率{self.memory_percent:.1f}%"
        elif status_level == "warning":
            return f"感觉有点累了，CPU使用率{self.cpu_percent:.1f}%，内存使用率{self.memory_percent:.1f}%"
        else:
            return f"感觉很累，需要休息一下，CPU使用率{self.cpu_percent:.1f}%，内存使用率{self.memory_percent:.1f}%"


class DevicePerception:
    """设备运行状况感知器（性能优化版）"""

    def __init__(self):
        self.last_network_io = None
        self.last_network_time = None
        self.gpu_available = self._check_gpu_availability()

        # CPU采样优化：后台线程定期采样
        self._cpu_percent_cache = 0.0
        self._cpu_sample_interval = 2.0  # 默认2秒采样一次
        self._cpu_sampling_lock = threading.Lock()
        self._cpu_sampling_thread = None
        self._stop_sampling = threading.Event()

        # 启动后台CPU采样线程
        self._start_cpu_sampling()

        logger.info(f"设备感知模块初始化完成，GPU可用: {self.gpu_available}, 后台CPU采样已启动")

    def _start_cpu_sampling(self):
        """启动后台CPU采样线程"""
        if self._cpu_sampling_thread and self._cpu_sampling_thread.is_alive():
            return

        self._stop_sampling.clear()
        self._cpu_sampling_thread = threading.Thread(
            target=self._cpu_sampling_loop,
            name="DevicePerception-CPU-Sampler",
            daemon=True
        )
        self._cpu_sampling_thread.start()
        logger.debug("CPU后台采样线程已启动")

    def _cpu_sampling_loop(self):
        """CPU采样循环（后台线程）"""
        # 首次调用需要interval参数来初始化
        psutil.cpu_percent(interval=0.1)

        while not self._stop_sampling.is_set():
            try:
                # 非阻塞方式获取CPU使用率（使用上次调用以来的平均值）
                cpu_percent = psutil.cpu_percent(interval=None)

                with self._cpu_sampling_lock:
                    self._cpu_percent_cache = cpu_percent

                # 等待下次采样
                self._stop_sampling.wait(self._cpu_sample_interval)

            except Exception as e:
                logger.error(f"CPU采样失败: {e}")
                self._stop_sampling.wait(5)  # 出错后等待5秒

    def stop_sampling(self):
        """停止后台采样（清理资源）"""
        logger.debug("正在停止CPU后台采样...")
        self._stop_sampling.set()
        if self._cpu_sampling_thread:
            self._cpu_sampling_thread.join(timeout=3)
        logger.info("CPU后台采样已停止")

    def _check_gpu_availability(self) -> bool:
        """检查GPU是否可用"""
        try:
            import pynvml
            pynvml.nvmlInit()
            return True
        except Exception:
            return False

    def get_cpu_info(self) -> Dict[str, Any]:
        """
        获取CPU信息（性能优化版 - 无阻塞）

        使用后台采样的缓存值，立即返回，不会阻塞
        """
        try:
            cpu_freq = psutil.cpu_freq()

            # 使用缓存的CPU百分比（后台线程采样）
            with self._cpu_sampling_lock:
                cpu_percent = self._cpu_percent_cache

            return {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "freq_current": cpu_freq.current if cpu_freq else 0.0,
                "freq_max": cpu_freq.max if cpu_freq else 0.0,
            }
        except Exception as e:
            logger.error(f"获取CPU信息失败: {e}")
            return {
                "percent": 0.0,
                "count": 0,
                "freq_current": 0.0,
                "freq_max": 0.0,
            }

    def get_memory_info(self) -> Dict[str, Any]:
        """获取内存信息"""
        try:
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "used": mem.used,
                "percent": mem.percent,
                "available": mem.available,
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {e}")
            return {
                "total": 0,
                "used": 0,
                "percent": 0.0,
                "available": 0,
            }

    def get_disk_info(self, path: str = "/") -> Dict[str, Any]:
        """获取磁盘信息"""
        try:
            disk = psutil.disk_usage(path)
            return {
                "total": disk.total,
                "used": disk.used,
                "percent": disk.percent,
                "free": disk.free,
            }
        except Exception as e:
            logger.error(f"获取磁盘信息失败: {e}")
            return {
                "total": 0,
                "used": 0,
                "percent": 0.0,
                "free": 0,
            }

    def get_network_info(self) -> Dict[str, Any]:
        """获取网络信息"""
        try:
            current_io = psutil.net_io_counters()
            current_time = time.time()

            result = {
                "sent": current_io.bytes_sent,
                "recv": current_io.bytes_recv,
                "sent_rate": 0.0,
                "recv_rate": 0.0,
            }

            # 计算速率
            if self.last_network_io and self.last_network_time:
                time_delta = current_time - self.last_network_time
                if time_delta > 0:
                    result["sent_rate"] = (current_io.bytes_sent - self.last_network_io.bytes_sent) / time_delta
                    result["recv_rate"] = (current_io.bytes_recv - self.last_network_io.bytes_recv) / time_delta

            self.last_network_io = current_io
            self.last_network_time = current_time

            return result
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {
                "sent": 0,
                "recv": 0,
                "sent_rate": 0.0,
                "recv_rate": 0.0,
            }

    def get_gpu_info(self) -> Dict[str, Any]:
        """获取GPU信息"""
        if not self.gpu_available:
            return {
                "available": False,
                "percent": 0.0,
                "memory_used": 0,
                "memory_total": 0,
                "memory_percent": 0.0,
                "temperature": 0.0,
            }

        try:
            import pynvml

            # 使用第一个GPU设备
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)

            # 获取GPU利用率
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

            # 获取显存信息
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

            # 获取温度
            try:
                temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temperature = 0.0

            return {
                "available": True,
                "percent": float(utilization.gpu),
                "memory_used": mem_info.used,
                "memory_total": mem_info.total,
                "memory_percent": (mem_info.used / mem_info.total * 100) if mem_info.total > 0 else 0.0,
                "temperature": float(temperature),
            }
        except Exception as e:
            logger.error(f"获取GPU信息失败: {e}")
            return {
                "available": False,
                "percent": 0.0,
                "memory_used": 0,
                "memory_total": 0,
                "memory_percent": 0.0,
                "temperature": 0.0,
            }

    def get_load_avg(self) -> Dict[str, float]:
        """获取系统负载"""
        try:
            load = psutil.getloadavg()
            return {
                "1min": load[0],
                "5min": load[1],
                "15min": load[2],
            }
        except Exception as e:
            logger.error(f"获取系统负载失败: {e}")
            return {
                "1min": 0.0,
                "5min": 0.0,
                "15min": 0.0,
            }

    def get_device_status(self) -> DeviceStatus:
        """
        获取完整的设备状态

        Returns:
            DeviceStatus对象
        """
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        network_info = self.get_network_info()
        gpu_info = self.get_gpu_info()
        load_avg = self.get_load_avg()

        return DeviceStatus(
            # CPU
            cpu_percent=cpu_info["percent"],
            cpu_count=cpu_info["count"],
            cpu_freq_current=cpu_info["freq_current"],
            cpu_freq_max=cpu_info["freq_max"],

            # 内存
            memory_total=memory_info["total"],
            memory_used=memory_info["used"],
            memory_percent=memory_info["percent"],
            memory_available=memory_info["available"],

            # 磁盘
            disk_total=disk_info["total"],
            disk_used=disk_info["used"],
            disk_percent=disk_info["percent"],
            disk_free=disk_info["free"],

            # 网络
            network_sent=network_info["sent"],
            network_recv=network_info["recv"],
            network_sent_rate=network_info["sent_rate"],
            network_recv_rate=network_info["recv_rate"],

            # GPU
            gpu_available=gpu_info["available"],
            gpu_percent=gpu_info["percent"],
            gpu_memory_used=gpu_info["memory_used"],
            gpu_memory_total=gpu_info["memory_total"],
            gpu_memory_percent=gpu_info["memory_percent"],
            gpu_temperature=gpu_info["temperature"],

            # 系统负载
            load_avg_1min=load_avg["1min"],
            load_avg_5min=load_avg["5min"],
            load_avg_15min=load_avg["15min"],

            # 时间戳
            timestamp=time.time(),
        )
