"""测试命令处理模块

提供测试功能的处理（仅超级管理员可用）
"""

import json
import re

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
        self._analyze_groups: set[str] = set()

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
        elif "分析" in message_str:
            await self._test_analyze(event)
        else:
            await event.send(event.plain_result("可用子命令：分享、分析（在当前群发送可开启/关闭该群的分析）"))

    async def _test_share(self, event: AiocqhttpMessageEvent) -> None:
        """测试分享功能

        Args:
            event: 消息事件对象
        """
        try:
            result = await event.bot.call_action(
                "get_mini_app_ark",
                type="bili",
                title="桑多涅 Jeb Nid Nid 【原神MMD】",
                desc="桑多涅 Jeb Nid Nid 【原神MMD】",
                picUrl="",
                jumpUrl="https://www.bilibili.com/video/BV1FAcfzJE3Q",
                webUrl="https://www.bilibili.com/video/BV1FAcfzJE3Q",
            )

            json_data = result.get("data", {})
            chain = [Comp.Json(data=json_data)]
            await event.send(event.chain_result(chain))
            logger.info("[LuwanPlugin] Bilibili小程序卡片已发送")
        except Exception as e:
            logger.error(f"[LuwanPlugin] 获取小程序卡片失败: {e}")
            await event.send(event.plain_result(f"❌ 获取小程序卡片失败: {e}"))

    async def _test_analyze(self, event: AiocqhttpMessageEvent) -> None:
        """测试分析功能

        Args:
            event: 消息事件对象
        """
        group_id = event.get_group_id()
        if not group_id:
            await event.send(event.plain_result("❌ 无法获取群号"))
            return

        if group_id in self._analyze_groups:
            self._analyze_groups.discard(group_id)
            await event.send(event.plain_result(f"✅ 已关闭当前群的分析功能"))
            logger.info(f"[LuwanPlugin] 已关闭群 {group_id} 的分析功能")
        else:
            self._analyze_groups.add(group_id)
            await event.send(event.plain_result(f"✅ 已开启当前群的分析功能"))
            logger.info(f"[LuwanPlugin] 已开启群 {group_id} 的分析功能")

    async def should_analyze(self, group_id: str) -> bool:
        """检查是否应该分析某群的消息

        Args:
            group_id: 群号

        Returns:
            是否应该分析
        """
        return group_id in self._analyze_groups

    async def analyze_message(self, event: AiocqhttpMessageEvent) -> None:
        """分析并转发消息内容

        Args:
            event: 消息事件对象
        """
        group_id = event.get_group_id()
        if not group_id or not await self.should_analyze(group_id):
            return

        try:
            message_chain = event.message_chain
            analysis_parts = []

            for segment in message_chain:
                if hasattr(segment, "type"):
                    if segment.type == "json":
                        json_data = getattr(segment, "data", {})
                        if isinstance(json_data, str):
                            try:
                                json_data = json.loads(json_data)
                            except Exception:
                                pass
                        analysis_parts.append(
                            f"📦 JSON:\n{json.dumps(json_data, ensure_ascii=False, indent=2)}"
                        )
                    elif segment.type == "image":
                        analysis_parts.append(
                            f"🖼️ 图片: {getattr(segment, 'url', 'N/A')}"
                        )
                    elif segment.type == "text":
                        analysis_parts.append(f"📝 文本: {segment.data}")
                    else:
                        analysis_parts.append(f"🔧 {segment.type}: {segment.data}")

            if analysis_parts:
                analysis_text = "\n\n".join(analysis_parts)
                await event.send(
                    event.plain_result(
                        f"🔍 群 {group_id} 消息分析\n━━━━━━━━━━━━━━\n{analysis_text}\n━━━━━━━━━━━━━━"
                    )
                )
        except Exception as e:
            logger.error(f"[LuwanPlugin] 分析消息失败: {e}")
