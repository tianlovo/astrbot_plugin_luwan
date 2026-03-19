"""禁言我处理模块

处理"禁言我"命令，将用户禁言指定时长
"""

from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..infra import LuwanConfig


class MuteHandler:
    """禁言我处理器

    处理用户自愿被禁言的请求
    """

    def __init__(self, config: LuwanConfig):
        """初始化处理器

        Args:
            config: 插件配置对象
        """
        self.config = config

    async def handle_mute_me(self, event: AiocqhttpMessageEvent) -> None:
        """处理禁言我命令

        Args:
            event: 消息事件对象
        """
        try:
            user_id = event.get_sender_id()
            group_id = event.get_group_id()

            if not group_id or not user_id:
                return

            if not self.config.mute_enabled:
                return

            if group_id not in self.config.mute_enabled_groups:
                return

            duration_minutes = self.config.mute_duration
            duration_seconds = duration_minutes * 60

            await event.bot.set_group_ban(
                group_id=int(group_id),
                user_id=int(user_id),
                duration=duration_seconds,
            )

            logger.info(
                f"[LuwanPlugin] 用户 {user_id} 在群 {group_id} 自愿被禁言 {duration_minutes} 分钟"
            )

        except Exception as e:
            logger.warning(f"[LuwanPlugin] 禁言失败: {e}")
