"""配置管理模块

提供插件配置的读取和管理功能
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.context import Context
from astrbot.core.star.star_tools import StarTools
from astrbot.core.utils.astrbot_path import get_astrbot_plugin_path


class LuwanConfig:
    """鹿丸插件配置类

    管理插件的所有配置项，提供便捷的访问方式
    """

    def __init__(self, config: AstrBotConfig, context: Context):
        """初始化配置

        Args:
            config: AstrBot 配置对象
            context: 插件上下文
        """
        self.config = config
        self.context = context

        # 获取 AstrBot 管理员列表
        self.admins_id = self._clean_ids(context.get_config().get("admins_id", []))

        # 设置数据目录
        self._plugin_name = "astrbot_plugin_luwan"
        self.data_dir = StarTools.get_data_dir(self._plugin_name)
        self.plugin_dir = Path(get_astrbot_plugin_path()) / self._plugin_name

        # 数据库路径
        self.db_path = self.data_dir / "luwan_data.db"

        logger.info(f"[LuwanPlugin] 数据目录: {self.data_dir}")

    @staticmethod
    def _clean_ids(ids: list) -> list[str]:
        """过滤并规范化数字 ID

        Args:
            ids: ID 列表

        Returns:
            规范化后的字符串 ID 列表
        """
        return [str(i) for i in ids if str(i).isdigit()]

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项

        Args:
            key: 配置项键名
            default: 默认值

        Returns:
            配置项值
        """
        return self.config.get(key, default)

    @property
    def forward_target_qq(self) -> str:
        """获取头衔申请转发目标 QQ"""
        return self.get("forward_target_qq", "")

    @property
    def command_prefix(self) -> str:
        """获取指令前缀"""
        return self.get("command_prefix", "")

    @property
    def min_interval(self) -> int:
        """获取最小申请间隔（分钟）"""
        rate_limit = self.get("rate_limit", {})
        return rate_limit.get("min_interval", 5)

    @property
    def daily_limit(self) -> int:
        """获取每日申请次数上限"""
        rate_limit = self.get("rate_limit", {})
        return rate_limit.get("daily_limit", 3)

    @property
    def super_admin(self) -> str:
        """获取超级管理员 QQ"""
        return self.get("super_admin", "")

    @property
    def auto_approve(self) -> bool:
        """是否自动批准头衔申请"""
        return self.get("auto_approve", False)

    # ==================== ComuPik 配置 ====================

    @property
    def comupik_enabled(self) -> bool:
        """是否启用 ComuPik 图片转发功能"""
        comupik = self.get("comupik", {})
        return comupik.get("enabled", True)

    @property
    def comupik_api_url(self) -> str:
        """ComuPik API 地址"""
        comupik = self.get("comupik", {})
        return comupik.get("api_url", "http://127.0.0.1:8080")

    @property
    def comupik_target_groups(self) -> list[str]:
        """ComuPik 图片转发目标 QQ 群列表"""
        comupik = self.get("comupik", {})
        groups = comupik.get("target_groups", [])
        return self._clean_ids(groups)

    @property
    def comupik_poll_interval(self) -> int:
        """ComuPik 轮询间隔（秒）"""
        comupik = self.get("comupik", {})
        return comupik.get("poll_interval", 30)

    @property
    def comupik_poll_time_range(self) -> int:
        """ComuPik 轮询时间范围（小时）"""
        comupik = self.get("comupik", {})
        return comupik.get("poll_time_range", 12)

    # ==================== 群打卡配置 ====================

    @property
    def group_checkin_enabled(self) -> bool:
        """是否启用群打卡功能"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("enabled", False)

    @property
    def group_checkin_target_groups(self) -> list[str]:
        """群打卡目标QQ群列表"""
        group_checkin = self.get("group_checkin", {})
        groups = group_checkin.get("target_groups", [])
        return self._clean_ids(groups)

    @property
    def group_checkin_timezone(self) -> str:
        """群打卡时区"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("timezone", "Asia/Shanghai")

    @property
    def group_checkin_start_time(self) -> str:
        """群打卡开始时间（HH:MM）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("start_time", "09:00")

    @property
    def group_checkin_end_time(self) -> str:
        """群打卡结束时间（HH:MM）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("end_time", "23:00")

    @property
    def group_checkin_desire(self) -> int:
        """群打卡欲望（0-100）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("desire", 50)

    @property
    def group_checkin_interval(self) -> int:
        """群打卡检查间隔（分钟）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("check_interval", 10)

    @property
    def group_checkin_enable_guarantee(self) -> bool:
        """是否启用打卡保底功能"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("enable_guarantee", False)

    @property
    def group_checkin_guarantee_check_time(self) -> str:
        """打卡保底检查时间（HH:MM）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("guarantee_check_time", "22:00")

    @property
    def group_checkin_guarantee_start_time(self) -> str:
        """打卡保底统计开始时间（HH:MM）"""
        group_checkin = self.get("group_checkin", {})
        return group_checkin.get("guarantee_start_time", "00:00")

    # ==================== 戳一戳配置 ====================

    @property
    def poke_enabled(self) -> bool:
        """是否启用戳一戳功能"""
        poke = self.get("poke", {})
        return poke.get("enabled", False)

    @property
    def poke_enabled_groups(self) -> list[str]:
        """戳一戳启用群列表"""
        poke = self.get("poke", {})
        groups = poke.get("enabled_groups", [])
        return self._clean_ids(groups)

    @property
    def poke_trigger_words(self) -> list[str]:
        """戳一戳触发词列表"""
        poke = self.get("poke", {})
        return poke.get("trigger_words", ["戳", "机器人", "bot"])

    @property
    def poke_beta0(self) -> float:
        """戳一戳基础概率参数 β0"""
        poke = self.get("poke", {})
        return poke.get("beta0", -2.0)

    @property
    def poke_beta1(self) -> float:
        """戳一戳触发词权重 β1"""
        poke = self.get("poke", {})
        return poke.get("beta1", 3.0)

    @property
    def poke_beta2(self) -> float:
        """戳一戳管理员权重 β2"""
        poke = self.get("poke", {})
        return poke.get("beta2", -2.0)

    @property
    def poke_beta3(self) -> float:
        """戳一戳时间间隔权重 β3"""
        poke = self.get("poke", {})
        return poke.get("beta3", 1.0)

    @property
    def poke_beta4(self) -> float:
        """戳一戳群活跃度权重 β4"""
        poke = self.get("poke", {})
        return poke.get("beta4", 1.0)

    @property
    def poke_beta5(self) -> float:
        """戳一戳时间段权重 β5"""
        poke = self.get("poke", {})
        return poke.get("beta5", 0.5)

    @property
    def poke_cooldown_hours(self) -> float:
        """戳一戳冷却时间（小时）"""
        poke = self.get("poke", {})
        return poke.get("cooldown_hours", 1.0)

    @property
    def poke_antipoke_enabled(self) -> bool:
        """是否启用反戳功能（被戳时戳回去）"""
        poke = self.get("poke", {})
        return poke.get("antipoke_enabled", False)

    @property
    def poke_antipoke_prob(self) -> float:
        """反戳概率"""
        poke = self.get("poke", {})
        return poke.get("antipoke_prob", 1.0)

    @property
    def poke_antipoke_max_times(self) -> int:
        """反戳最大次数"""
        poke = self.get("poke", {})
        return poke.get("antipoke_max_times", 1)

    @property
    def poke_follow_enabled(self) -> bool:
        """是否启用跟戳功能（其他人被戳时随机跟戳）"""
        poke = self.get("poke", {})
        return poke.get("follow_enabled", False)

    @property
    def poke_follow_prob(self) -> float:
        """跟戳概率"""
        poke = self.get("poke", {})
        return poke.get("follow_prob", 0.3)

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否为管理员

        Args:
            user_id: 用户 QQ 号

        Returns:
            是否为管理员
        """
        user_id = str(user_id)

        # 检查是否为 AstrBot 管理员
        if user_id in self.admins_id:
            return True

        # 检查是否为插件超级管理员
        if self.super_admin and user_id == self.super_admin:
            return True

        return False
