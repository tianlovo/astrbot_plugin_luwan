"""帮助菜单处理模块

提供插件帮助信息的显示功能
"""

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..messages import Messages


class HelpHandler:
    """帮助菜单处理器

    显示插件的帮助信息和使用说明
    """

    def __init__(self, min_interval: int = 5, daily_limit: int = 3):
        """初始化帮助处理器

        Args:
            min_interval: 最小申请间隔（分钟）
            daily_limit: 每日申请次数上限
        """
        self.min_interval = min_interval
        self.daily_limit = daily_limit

    def get_help_text(self, is_admin: bool = False) -> str:
        """获取帮助菜单文本

        Args:
            is_admin: 是否为管理员

        Returns:
            格式化的帮助菜单
        """
        if is_admin:
            return Messages.get(
                "help.menu_admin",
                min_interval=self.min_interval,
                daily_limit=self.daily_limit,
            )
        else:
            return Messages.get(
                "help.menu_user",
                min_interval=self.min_interval,
                daily_limit=self.daily_limit,
            )

    async def show_menu(
        self, event: AiocqhttpMessageEvent, is_admin: bool = False
    ) -> None:
        """显示帮助菜单

        Args:
            event: 消息事件对象
            is_admin: 是否为管理员
        """
        help_text = self.get_help_text(is_admin)
        await event.send(event.plain_result(help_text))

    def update_rate_limit(self, min_interval: int, daily_limit: int) -> None:
        """更新频率限制显示参数

        Args:
            min_interval: 最小申请间隔（分钟）
            daily_limit: 每日申请次数上限
        """
        self.min_interval = min_interval
        self.daily_limit = daily_limit
