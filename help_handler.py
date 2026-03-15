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

    # 帮助菜单文本
    HELP_MENU = """
🌟 【鹿丸插件帮助菜单】 🌟

━━━━━━━━━━━━━━━━━━━━━━
📋 基础指令
━━━━━━━━━━━━━━━━━━━━━━
• 菜单 / 帮助 / help
  显示本帮助菜单

━━━━━━━━━━━━━━━━━━━━━━
🏷️ 头衔申请
━━━━━━━━━━━━━━━━━━━━━━
• 申请头衔 <头衔名称>
  申请一个新的群头衔
  别名：我要头衔
  示例：申请头衔 小可爱

• 换头衔 <新头衔名称>
  更换已有的群头衔
  别名：更换头衔
  示例：换头衔 大可爱

⚠️ 注意事项：
  - 申请后需要群主批准
  - 每次申请间隔 {min_interval} 分钟
  - 每日最多申请 {daily_limit} 次

━━━━━━━━━━━━━━━━━━━━━━
⚙️ 管理员指令
━━━━━━━━━━━━━━━━━━━━━━
• 鹿丸配置
  查看当前插件配置
  别名：lw配置

• 鹿丸配置 <配置项> <值>
  修改插件配置
  示例：鹿丸配置 forward_target_qq 123456789

━━━━━━━━━━━━━━━━━━━━━━
💡 提示
━━━━━━━━━━━━━━━━━━━━━━
• 所有指令均需要在群聊中使用
• 部分指令需要 @机器人
• 如有问题请联系群管理员

━━━━━━━━━━━━━━━━━━━━━━
"""

    def __init__(self, min_interval: int = 5, daily_limit: int = 3):
        """初始化帮助处理器

        Args:
            min_interval: 最小申请间隔（分钟）
            daily_limit: 每日申请次数上限
        """
        self.min_interval = min_interval
        self.daily_limit = daily_limit

    def get_help_text(self) -> str:
        """获取帮助菜单文本

        Returns:
            格式化的帮助菜单
        """
        return self.HELP_MENU.format(
            min_interval=self.min_interval,
            daily_limit=self.daily_limit,
        )

    async def show_menu(self, event: AiocqhttpMessageEvent) -> None:
        """显示帮助菜单

        Args:
            event: 消息事件对象
        """
        help_text = self.get_help_text()
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
