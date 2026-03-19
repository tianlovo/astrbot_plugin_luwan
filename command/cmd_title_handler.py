"""头衔申请处理模块

处理用户的头衔申请、频率限制检查和转发功能
"""

import re
from datetime import datetime

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..config import LuwanConfig
from ..database import LuwanDB


class TitleHandler:
    """头衔申请处理器

    处理头衔申请相关的业务逻辑
    """

    def __init__(self, config: LuwanConfig, db: LuwanDB):
        """初始化处理器

        Args:
            config: 插件配置对象
            db: 数据库对象
        """
        self.config = config
        self.db = db

    def _validate_title(self, title: str) -> tuple[bool, str]:
        """验证头衔格式

        Args:
            title: 申请的头衔名称

        Returns:
            (是否有效, 错误提示)
        """
        # 检查是否为空
        if not title:
            return False, "❌ 请输入头衔名称"

        # 检查是否包含空格
        if " " in title or "\u3000" in title:
            return False, "❌ 头衔不能包含空格"

        # 检查长度（单字母、单空格等都算一个字符）
        if len(title) > 5:
            return False, "❌ 头衔长度不能超过5个字符"

        return True, ""

    async def handle_apply_title(
        self, event: AiocqhttpMessageEvent, title: str, is_change: bool = False
    ) -> None:
        """处理头衔申请

        Args:
            event: 消息事件对象
            title: 申请的头衔名称
            is_change: 是否为更换头衔
        """
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        user_name = event.get_sender_name()

        # 验证头衔格式
        is_valid, error_msg = self._validate_title(title)
        if not is_valid:
            await event.send(event.plain_result(error_msg))
            return

        # 检查频率限制
        can_apply, message = await self.db.check_rate_limit(
            user_id, self.config.min_interval, self.config.daily_limit
        )

        if not can_apply:
            await event.send(event.plain_result(message))
            return

        # 检查是否设置了转发目标
        if not self.config.forward_target_qq:
            await event.send(
                event.plain_result("❌ 插件未配置转发目标QQ，请联系管理员配置")
            )
            return

        # 记录申请到数据库
        success = await self.db.add_application(user_id, group_id, title)
        if not success:
            await event.send(event.plain_result("❌ 申请记录失败，请稍后重试"))
            return

        # 记录频率限制
        await self.db.record_application(user_id)

        # 转发申请给群主
        await self._forward_to_owner(
            event, user_id, user_name, group_id, title, is_change
        )

        # 返回用户响应（引用消息并 @ 用户）
        action_text = "更换" if is_change else "申请"
        message_id = event.message_obj.message_id
        user_id = event.get_sender_id()

        # 构建消息组件：引用 + @用户 + 文本
        chain = [
            Comp.Reply(id=message_id),
            Comp.At(qq=user_id),
            Comp.Plain(
                f"\n✅ 已{action_text}头衔「{title}」\n📢 已通知群主处理，请耐心等待"
            ),
        ]
        await event.send(event.chain_result(chain))

        logger.info(
            f"[LuwanPlugin] 用户 {user_name}({user_id}) 在群 {group_id} "
            f"{action_text}头衔: {title}"
        )

    async def _forward_to_owner(
        self,
        event: AiocqhttpMessageEvent,
        user_id: str,
        user_name: str,
        group_id: str,
        title: str,
        is_change: bool = False,
    ) -> None:
        """将申请信息转发给群主

        Args:
            event: 消息事件对象
            user_id: 申请人QQ号
            user_name: 申请人昵称
            group_id: 群号
            title: 申请的头衔
            is_change: 是否为更换头衔
        """
        try:
            # 获取群信息
            group_info = await event.bot.get_group_info(group_id=int(group_id))
            group_name = (
                group_info.get("group_name", group_id) if group_info else group_id
            )
        except Exception:
            group_name = group_id

        # 构建转发消息
        action_text = "更换" if is_change else "申请"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        forward_message = (
            f"📋 头衔{action_text}通知\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 申请人：{user_name}({user_id})\n"
            f"👥 来源群：{group_name}({group_id})\n"
            f"🏷️ 申请头衔：{title}\n"
            f"⏰ 申请时间：{current_time}\n"
            f"━━━━━━━━━━━━━━"
        )

        try:
            # 私聊发送给群主 - 通知消息
            forward_msg = await event.bot.send_private_msg(
                user_id=int(self.config.forward_target_qq),
                message=forward_message,
            )

            # 获取转发消息的消息ID用于引用
            forward_msg_id = None
            if forward_msg and isinstance(forward_msg, dict):
                forward_msg_id = forward_msg.get("message_id")

            # 额外发送头衔内容，方便群主复制，并引用详细消息
            if forward_msg_id:
                # 构建引用消息
                title_message = [
                    {"type": "reply", "data": {"id": str(forward_msg_id)}},
                    {"type": "text", "data": {"text": title}},
                ]
                await event.bot.send_private_msg(
                    user_id=int(self.config.forward_target_qq),
                    message=title_message,
                )
            else:
                # 无法获取消息ID时直接发送
                await event.bot.send_private_msg(
                    user_id=int(self.config.forward_target_qq),
                    message=title,
                )

            logger.info(
                f"[LuwanPlugin] 已转发头衔申请到 {self.config.forward_target_qq}"
            )
        except Exception as e:
            logger.error(f"[LuwanPlugin] 转发申请失败: {e}")

    async def handle_change_title(
        self, event: AiocqhttpMessageEvent, new_title: str
    ) -> None:
        """处理更换头衔

        Args:
            event: 消息事件对象
            new_title: 新头衔名称
        """
        await self.handle_apply_title(event, new_title, is_change=True)

    async def handle_remove_title(self, event: AiocqhttpMessageEvent) -> None:
        """处理移除头衔

        Args:
            event: 消息事件对象
        """
        user_id = event.get_sender_id()
        group_id = event.get_group_id()
        user_name = event.get_sender_name()

        # 检查频率限制
        can_apply, message = await self.db.check_rate_limit(
            user_id, self.config.min_interval, self.config.daily_limit
        )

        if not can_apply:
            await event.send(event.plain_result(message))
            return

        # 检查是否设置了转发目标
        if not self.config.forward_target_qq:
            await event.send(
                event.plain_result("❌ 插件未配置转发目标QQ，请联系管理员配置")
            )
            return

        # 记录频率限制
        await self.db.record_application(user_id)

        # 转发移除请求给群主
        await self._forward_remove_to_owner(event, user_id, user_name, group_id)

        # 返回用户响应（引用消息并 @ 用户）
        message_id = event.message_obj.message_id
        user_id = event.get_sender_id()

        # 构建消息组件：引用 + @用户 + 文本
        chain = [
            Comp.Reply(id=message_id),
            Comp.At(qq=user_id),
            Comp.Plain("\n✅ 已申请移除头衔\n📢 已通知群主处理，请耐心等待"),
        ]
        await event.send(event.chain_result(chain))

        logger.info(
            f"[LuwanPlugin] 用户 {user_name}({user_id}) 在群 {group_id} 申请移除头衔"
        )

    async def _forward_remove_to_owner(
        self,
        event: AiocqhttpMessageEvent,
        user_id: str,
        user_name: str,
        group_id: str,
    ) -> None:
        """将移除头衔请求转发给群主

        Args:
            event: 消息事件对象
            user_id: 申请人QQ号
            user_name: 申请人昵称
            group_id: 群号
        """
        try:
            # 获取群信息
            group_info = await event.bot.get_group_info(group_id=int(group_id))
            group_name = (
                group_info.get("group_name", group_id) if group_info else group_id
            )
        except Exception:
            group_name = group_id

        # 构建转发消息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        forward_message = (
            f"📋 头衔移除通知\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 申请人：{user_name}({user_id})\n"
            f"👥 来源群：{group_name}({group_id})\n"
            f"🏷️ 操作：移除头衔\n"
            f"⏰ 申请时间：{current_time}\n"
            f"━━━━━━━━━━━━━━"
        )

        try:
            # 私聊发送给群主
            await event.bot.send_private_msg(
                user_id=int(self.config.forward_target_qq),
                message=forward_message,
            )

            logger.info(
                f"[LuwanPlugin] 已转发头衔移除申请到 {self.config.forward_target_qq}"
            )
        except Exception as e:
            logger.error(f"[LuwanPlugin] 转发移除申请失败: {e}")

    def extract_title_from_message(self, message_str: str, command: str) -> str | None:
        """从消息中提取头衔名称

        Args:
            message_str: 完整消息字符串
            command: 指令部分（如"申请头衔"）

        Returns:
            提取的头衔名称，如果未提供则返回 None
        """
        # 使用正则表达式匹配指令，支持多个空格
        # 模式：指令 + 一个或多个空格 + 头衔内容
        pattern = rf"{re.escape(command)}\s+(.+)"
        match = re.search(pattern, message_str)

        if match:
            title = match.group(1).strip()
            # 移除可能的前缀符号
            title = title.lstrip("/!!").strip()
            if title:
                return title

        return None
