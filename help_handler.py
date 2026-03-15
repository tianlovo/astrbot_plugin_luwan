"""帮助菜单处理模块

提供插件帮助信息的显示功能
"""

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


class HelpHandler:
    """帮助菜单处理器

    显示插件的帮助信息和使用说明
    """

    # 普通用户帮助菜单（精简版）
    HELP_MENU_USER = """
📋 指令列表
━━━━━━━━━━━━━━
• 菜单 / 帮助 / help
  显示本帮助菜单

🏷️ 头衔管理
━━━━━━━━━━━━━━
• 头衔 <名称>
  别名：申请头衔、我要头衔、换头衔、更换头衔
  示例：
    头衔 小可爱（申请/更换）
    头衔 无（移除头衔）

⚠️ 限制：间隔 {min_interval} 分钟，每日 {daily_limit} 次
"""

    # 管理员帮助菜单（完整版）
    HELP_MENU_ADMIN = """
📋 指令列表
━━━━━━━━━━━━━━
• 菜单 / 帮助 / help
  显示本帮助菜单

🏷️ 头衔管理
━━━━━━━━━━━━━━
• 头衔 <名称>
  别名：申请头衔、我要头衔、换头衔、更换头衔
  示例：
    头衔 小可爱（申请/更换）
    头衔 无（移除头衔）

⚠️ 限制：间隔 {min_interval} 分钟，每日 {daily_limit} 次

⚙️ 管理指令
━━━━━━━━━━━━━━
• 鹿丸配置
  查看当前配置

• 鹿丸配置 <项> <值>
  修改配置
  示例：鹿丸配置 forward_target_qq 123456
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
        menu = self.HELP_MENU_ADMIN if is_admin else self.HELP_MENU_USER
        return menu.format(
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
        event.stop_event()

    def update_rate_limit(self, min_interval: int, daily_limit: int) -> None:
        """更新频率限制显示参数

        Args:
            min_interval: 最小申请间隔（分钟）
            daily_limit: 每日申请次数上限
        """
        self.min_interval = min_interval
        self.daily_limit = daily_limit
