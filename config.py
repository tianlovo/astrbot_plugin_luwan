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
