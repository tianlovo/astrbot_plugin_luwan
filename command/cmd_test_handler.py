"""测试命令处理模块

提供测试功能的处理（仅超级管理员可用）
"""

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..infra import LuwanConfig


class TestHandler:
    """测试命令处理器

    提供测试功能的处理（仅超级管理员可用）
    """

    def __init__(self, config: LuwanConfig):
        """初始化测试处理器

        Args:
            config: 插件配置对象
        """
        self.config = config

    async def handle_test(self, event: AiocqhttpMessageEvent) -> None:
        """处理测试命令

        Args:
            event: 消息事件对象
        """
        user_id = event.get_sender_id()

        if not self.config.is_admin(user_id):
            await event.send(event.plain_result("❌ 仅超级管理员可使用此命令"))
            return

        message_str = event.message_str.strip()

        if "分享" in message_str:
            await self._test_share(event)
        else:
            await event.send(event.plain_result("可用子命令：分享"))

    async def _test_share(self, event: AiocqhttpMessageEvent) -> None:
        """测试分享功能

        Args:
            event: 消息事件对象
        """
        url = "https://www.bilibili.com/video/BV1FAcfzJE3Q"
        title = "桑多涅 Jeb Nid Nid 【原神MMD】"
        content = "测试分享内容"

        chain = Comp.MessageChain().append(
            Comp.Share(url=url, title=title, content=content, image=None)
        )
        await event.send(chain)
        logger.info("[LuwanPlugin] 测试分享消息已发送")
