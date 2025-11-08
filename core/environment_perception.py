"""
环境感知模块
感知时间、天气、节日等环境信息
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from src.common.logger import get_logger

logger = get_logger("environment_perception")


@dataclass
class EnvironmentStatus:
    """环境状态数据类"""

    # 时间相关
    timestamp: float = 0.0
    datetime_str: str = ""
    hour: int = 0
    minute: int = 0
    weekday: int = 0  # 0=周一, 6=周日
    is_weekend: bool = False
    is_workday: bool = True
    time_period: str = ""  # "dawn" | "morning" | "noon" | "afternoon" | "evening" | "night" | "midnight"

    # 节日相关
    is_holiday: bool = False
    holiday_name: str = ""
    special_date: str = ""  # 特殊日期描述

    # 天气相关（如果启用）
    weather_available: bool = False
    weather_description: str = ""
    temperature: float = 0.0
    humidity: float = 0.0
    weather_code: str = ""

    # 季节
    season: str = ""  # "spring" | "summer" | "autumn" | "winter"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_human_readable_summary(self) -> str:
        """获取人类可读的环境摘要"""
        parts = []

        # 时间描述
        time_desc = self._get_time_description()
        if time_desc:
            parts.append(time_desc)

        # 节日描述
        if self.is_holiday and self.holiday_name:
            parts.append(f"今天是{self.holiday_name}")

        # 天气描述
        if self.weather_available and self.weather_description:
            parts.append(f"天气{self.weather_description}")
            if self.temperature > 0:
                parts.append(f"气温{self.temperature:.1f}°C")

        return "，".join(parts) if parts else "现在是普通的一天"

    def _get_time_description(self) -> str:
        """获取时间描述"""
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        period_names = {
            "dawn": "黎明",
            "morning": "早上",
            "noon": "中午",
            "afternoon": "下午",
            "evening": "傍晚",
            "night": "晚上",
            "midnight": "深夜",
        }

        weekday_str = weekday_names[self.weekday]
        period_str = period_names.get(self.time_period, "")

        return f"{period_str}，{weekday_str}"


class EnvironmentPerception:
    """环境感知器"""

    # 中国法定节假日（简化版，实际应该从API获取）
    CHINESE_HOLIDAYS = {
        "01-01": "元旦",
        "02-14": "情人节",
        "03-08": "妇女节",
        "04-04": "清明节",
        "04-05": "清明节",
        "05-01": "劳动节",
        "05-04": "青年节",
        "06-01": "儿童节",
        "08-15": "中秋节",  # 农历，这里简化
        "10-01": "国庆节",
        "12-25": "圣诞节",
    }

    # 农历节日（需要农历转换库支持）
    LUNAR_HOLIDAYS = {
        "春节": "农历正月初一",
        "元宵节": "农历正月十五",
        "端午节": "农历五月初五",
        "七夕节": "农历七月初七",
        "中秋节": "农历八月十五",
        "重阳节": "农历九月初九",
    }

    def __init__(self, enable_weather: bool = False, weather_api_key: Optional[str] = None, location: str = ""):
        """
        初始化环境感知器

        Args:
            enable_weather: 是否启用天气感知
            weather_api_key: 天气API密钥
            location: 位置信息
        """
        self.enable_weather = enable_weather
        self.weather_api_key = weather_api_key
        self.location = location

        self.weather_cache: Optional[Dict[str, Any]] = None
        self.weather_cache_time: float = 0.0
        self.weather_cache_duration: float = 1800  # 30分钟缓存

        logger.info(f"环境感知模块初始化完成，天气感知: {enable_weather}")

    def get_time_period(self, hour: int) -> str:
        """
        根据小时获取时间段

        Args:
            hour: 小时 (0-23)

        Returns:
            时间段标识
        """
        if 4 <= hour < 6:
            return "dawn"  # 黎明
        elif 6 <= hour < 12:
            return "morning"  # 早上
        elif 12 <= hour < 13:
            return "noon"  # 中午
        elif 13 <= hour < 18:
            return "afternoon"  # 下午
        elif 18 <= hour < 20:
            return "evening"  # 傍晚
        elif 20 <= hour < 24:
            return "night"  # 晚上
        else:
            return "midnight"  # 深夜

    def get_season(self, month: int) -> str:
        """
        根据月份获取季节

        Args:
            month: 月份 (1-12)

        Returns:
            季节标识
        """
        if month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        elif month in [9, 10, 11]:
            return "autumn"
        else:
            return "winter"

    def check_holiday(self, date: datetime) -> tuple[bool, str]:
        """
        检查是否为节日

        Args:
            date: 日期对象

        Returns:
            (是否为节日, 节日名称)
        """
        date_str = date.strftime("%m-%d")

        if date_str in self.CHINESE_HOLIDAYS:
            return True, self.CHINESE_HOLIDAYS[date_str]

        # TODO: 添加农历节日支持，需要农历转换库
        # 这里可以集成 lunarcalendar 或 chinese-calendar 库

        return False, ""

    def get_special_date_description(self, date: datetime) -> str:
        """
        获取特殊日期描述

        Args:
            date: 日期对象

        Returns:
            特殊日期描述
        """
        # 检查是否为月初/月末
        if date.day == 1:
            return f"{date.month}月的第一天"
        elif date.day == 15:
            return "月中"

        # 检查最后一天
        next_month = date.replace(day=28) + timedelta(days=4)
        last_day = (next_month - timedelta(days=next_month.day)).day
        if date.day == last_day:
            return f"{date.month}月的最后一天"

        return ""

    async def get_weather_info(self) -> Optional[Dict[str, Any]]:
        """
        获取天气信息（需要天气API）

        Returns:
            天气信息字典，如果失败则返回None
        """
        if not self.enable_weather:
            return None

        # 检查缓存
        current_time = time.time()
        if self.weather_cache and (current_time - self.weather_cache_time) < self.weather_cache_duration:
            return self.weather_cache

        # TODO: 实现天气API调用
        # 这里可以集成 OpenWeatherMap、和风天气、心知天气等API
        # 示例实现（需要实际API）:
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.weather_api_key}&units=metric&lang=zh_cn"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        weather_info = {
                            "description": data["weather"][0]["description"],
                            "temperature": data["main"]["temp"],
                            "humidity": data["main"]["humidity"],
                            "code": data["weather"][0]["main"],
                        }
                        self.weather_cache = weather_info
                        self.weather_cache_time = current_time
                        return weather_info
        except Exception as e:
            logger.error(f"获取天气信息失败: {e}")
        """

        return None

    async def get_environment_status(self) -> EnvironmentStatus:
        """
        获取完整的环境状态

        Returns:
            EnvironmentStatus对象
        """
        now = datetime.now()

        # 时间信息
        hour = now.hour
        minute = now.minute
        weekday = now.weekday()
        is_weekend = weekday in [5, 6]
        is_workday = not is_weekend
        time_period = self.get_time_period(hour)

        # 节日信息
        is_holiday, holiday_name = self.check_holiday(now)
        special_date = self.get_special_date_description(now)

        # 季节
        season = self.get_season(now.month)

        # 天气信息
        weather_info = await self.get_weather_info()
        weather_available = weather_info is not None

        return EnvironmentStatus(
            timestamp=time.time(),
            datetime_str=now.strftime("%Y-%m-%d %H:%M:%S"),
            hour=hour,
            minute=minute,
            weekday=weekday,
            is_weekend=is_weekend,
            is_workday=is_workday,
            time_period=time_period,
            is_holiday=is_holiday,
            holiday_name=holiday_name,
            special_date=special_date,
            weather_available=weather_available,
            weather_description=weather_info.get("description", "") if weather_info else "",
            temperature=weather_info.get("temperature", 0.0) if weather_info else 0.0,
            humidity=weather_info.get("humidity", 0.0) if weather_info else 0.0,
            weather_code=weather_info.get("code", "") if weather_info else "",
            season=season,
        )
