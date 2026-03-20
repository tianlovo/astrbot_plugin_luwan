"""禁言我处理模块

处理"禁言我"和禁言投票命令
"""

import asyncio
import time
from dataclasses import dataclass, field

from astrbot.api import logger
from astrbot.api.message_components import At
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from ..infra import LuwanConfig


@dataclass
class MuteVoteSession:
    """禁言投票会话"""

    group_id: str
    target_user_id: str
    target_name: str
    initiator_user_id: str
    message_id: int
    start_time: float
    duration: int
    good_voters: set[str] = field(default_factory=set)
    bad_voters: set[str] = field(default_factory=set)
    all_voters: set[str] = field(default_factory=set)
    cancelled: bool = False
    bot: None = field(default=None)


class MuteHandler:
    """禁言我处理器

    处理用户自愿被禁言的请求和禁言投票功能
    """

    def __init__(self, config: LuwanConfig):
        """初始化处理器

        Args:
            config: 插件配置对象
        """
        self.config = config
        self._vote_sessions: dict[str, MuteVoteSession] = {}
        self._target_cooldown: dict[str, float] = {}

    def _get_vote_key(self, group_id: str, message_id: int) -> str:
        return f"{group_id}:{message_id}"

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

    async def handle_mute_request(self, event: AiocqhttpMessageEvent) -> None:
        """处理禁言投票请求

        命令格式: 禁言 @用户
        机器人 At 目标用户并发起投票

        Args:
            event: 消息事件对象
        """
        try:
            initiator_id = event.get_sender_id()
            group_id = event.get_group_id()

            if not group_id or not initiator_id:
                return

            if not self.config.mute_enabled:
                return

            if group_id not in self.config.mute_enabled_groups:
                return

            messages = event.get_messages()
            at_components = [comp for comp in messages if isinstance(comp, At)]

            if len(at_components) < 2:
                return

            target_user_id = str(at_components[1].qq)

            if target_user_id == str(event.bot.self_id):
                return

            target_name = target_user_id
            try:
                member_info = await event.bot.get_group_member_info(
                    group_id=int(group_id), user_id=int(target_user_id)
                )
                if member_info:
                    target_name = (
                        member_info.get("card")
                        or member_info.get("nickname")
                        or target_user_id
                    )
            except Exception:
                pass

            cooldown_key = f"{group_id}:{target_user_id}"
            current_time = time.time()
            if cooldown_key in self._target_cooldown:
                last_mute_time = self._target_cooldown[cooldown_key]
                elapsed = current_time - last_mute_time
                if elapsed < self.config.mute_target_cooldown:
                    remaining = int(self.config.mute_target_cooldown - elapsed)
                    logger.info(
                        f"[LuwanPlugin] 目标用户 {target_user_id} 在冷却期内，拒绝禁言投票"
                    )
                    await event.bot.send_group_msg(
                        group_id=int(group_id),
                        message=f"❌ 该用户正在禁言冷却中，请 {remaining} 秒后再试",
                    )
                    return

            # 检查当前群是否已有进行中的投票（一个群同时只能有一个投票）
            existing_vote_key = None
            for key, session in self._vote_sessions.items():
                if session.group_id == group_id and not session.cancelled:
                    if current_time - session.start_time < session.duration:
                        existing_vote_key = key
                        break

            if existing_vote_key:
                logger.info(f"[LuwanPlugin] 群 {group_id} 已有进行中的投票")
                return

            vote_key = f"{group_id}:{initiator_id}"

            vote_msg_obj = await event.bot.send_group_msg(
                group_id=int(group_id),
                message=[
                    {"type": "at", "data": {"qq": int(initiator_id)}},
                    {"type": "text", "data": {"text": " 发起了投票，各位是否要禁言 "}},
                    {"type": "at", "data": {"qq": int(target_user_id)}},
                    {
                        "type": "text",
                        "data": {
                            "text": f"？\n{self.config.mute_vote_duration}秒内发送「好」或「不好」来参与投票吧~"
                        },
                    },
                ],
            )

            session = MuteVoteSession(
                group_id=group_id,
                target_user_id=target_user_id,
                target_name=target_name,
                initiator_user_id=initiator_id,
                message_id=vote_msg_obj.get("message_id", 0),
                start_time=current_time,
                duration=self.config.mute_vote_duration,
                bot=event.bot,
            )
            self._vote_sessions[vote_key] = session

            asyncio.create_task(self._wait_for_vote_result(vote_key))

            logger.info(
                f"[LuwanPlugin] 用户 {initiator_id} 在群 {group_id} 发起禁言投票，目标: {target_user_id}"
            )

        except Exception as e:
            logger.warning(f"[LuwanPlugin] 禁言投票发起失败: {e}")

    async def on_group_message(
        self,
        group_id: str,
        user_id: str,
        message_text: str,
        bot_self_id: str | None = None,
    ) -> None:
        """处理群消息

        当有进行中的投票时，检测"好"或"不好"消息并计入投票

        Args:
            group_id: 群号
            user_id: 用户ID
            message_text: 消息文本
            bot_self_id: 机器人自身ID
        """
        try:
            if not group_id or group_id not in self.config.mute_enabled_groups:
                return

            if bot_self_id and user_id == bot_self_id:
                return

            message_text = message_text.strip()

            # 使用INFO级别确保日志可见
            logger.info(
                f"[MuteHandler] 收到消息 | 群:{group_id} | 用户:{user_id} | 内容:'{message_text}'"
            )
            logger.info(f"[MuteHandler] 当前投票会话数: {len(self._vote_sessions)}")

            # 处理 @机器人 的情况，如 "@机器人昵称(123456) 好"
            # 移除 @xxx(xxx) 格式的文本
            import re

            cleaned_text = re.sub(r"\s*@\S+?\(\d+\)\s*", " ", message_text).strip()
            # 再清理一次普通 @ 格式
            cleaned_text = re.sub(r"\s*@\S+\s*", " ", cleaned_text).strip()

            logger.info(f"[MuteHandler] 清理后文本: '{cleaned_text}'")

            if cleaned_text == "好" or message_text == "好":
                logger.info(f"[MuteHandler] 检测到'好'投票 | 用户:{user_id}")
                await self.handle_vote_response_raw(group_id, user_id, is_good=True)
            elif cleaned_text == "不好" or message_text == "不好":
                logger.info(f"[MuteHandler] 检测到'不好'投票 | 用户:{user_id}")
                await self.handle_vote_response_raw(group_id, user_id, is_good=False)
        except Exception as e:
            logger.warning(f"[LuwanPlugin] 处理投票消息失败: {e}", exc_info=True)

    async def handle_vote_response_raw(
        self, group_id: str, voter_id: str, is_good: bool
    ) -> None:
        """处理投票响应（原始参数）

        Args:
            group_id: 群号
            voter_id: 投票用户ID
            is_good: True 表示"好"，False 表示"不好"
        """
        try:
            if not group_id or not voter_id:
                logger.info(
                    f"[MuteHandler] 投票响应参数无效 | 群:{group_id} | 用户:{voter_id}"
                )
                return

            if not self.config.mute_enabled:
                logger.info("[MuteHandler] 禁言功能未启用")
                return

            if group_id not in self.config.mute_enabled_groups:
                logger.info(f"[MuteHandler] 群 {group_id} 不在启用列表中")
                return

            current_time = time.time()
            vote_key = None
            for key, session in self._vote_sessions.items():
                logger.info(
                    f"[MuteHandler] 检查会话 | key:{key} | 群:{session.group_id} | 取消:{session.cancelled} | 剩余时间:{session.duration - (current_time - session.start_time):.1f}s"
                )
                if (
                    session.group_id == group_id
                    and not session.cancelled
                    and current_time - session.start_time < session.duration
                ):
                    vote_key = key
                    break

            if not vote_key:
                logger.info(f"[MuteHandler] 未找到有效的投票会话 | 群:{group_id}")
                return

            session = self._vote_sessions[vote_key]
            logger.info(
                f"[MuteHandler] 找到投票会话 | key:{vote_key} | 目标:{session.target_user_id}"
            )

            if voter_id in session.all_voters:
                logger.info(f"[MuteHandler] 用户已投票 | 用户:{voter_id}")
                return

            session.all_voters.add(voter_id)

            if is_good:
                session.good_voters.add(voter_id)
                logger.info(
                    f"[MuteHandler] 投票记录: 用户 {voter_id} 投了好 | 当前好票数:{len(session.good_voters)}"
                )
            else:
                session.bad_voters.add(voter_id)
                logger.info(
                    f"[MuteHandler] 投票记录: 用户 {voter_id} 投了不好 | 当前不好票数:{len(session.bad_voters)}"
                )

        except Exception as e:
            logger.warning(f"[LuwanPlugin] 处理投票响应失败: {e}", exc_info=True)

    async def _wait_for_vote_result(self, vote_key: str) -> None:
        """等待投票结果

        Args:
            vote_key: 投票会话键
        """
        await asyncio.sleep(self._vote_sessions[vote_key].duration)

        session = self._vote_sessions.get(vote_key)
        if not session or session.cancelled:
            return

        session.cancelled = True

        good_count = len(session.good_voters)
        bad_count = len(session.bad_voters)

        logger.info(
            f"[LuwanPlugin] 投票结束 | 群 {session.group_id} | 目标 {session.target_user_id} | "
            f"好:{good_count} | 不好:{bad_count}"
        )

        if good_count > bad_count:
            try:
                duration_seconds = self.config.mute_duration * 60
                await session.bot.set_group_ban(
                    group_id=int(session.group_id),
                    user_id=int(session.target_user_id),
                    duration=duration_seconds,
                )

                cooldown_key = f"{session.group_id}:{session.target_user_id}"
                self._target_cooldown[cooldown_key] = time.time()

                logger.info(
                    f"[LuwanPlugin] 投票通过，禁言用户 {session.target_user_id} 在群 {session.group_id}"
                )

                result_message = f"投票结束！同意票({good_count}) > 反对票({bad_count})，执行禁言「{session.target_name}」"
            except Exception as e:
                logger.warning(f"[LuwanPlugin] 执行禁言失败: {e}")
                result_message = f"投票结束！同意票({good_count}) > 反对票({bad_count})，但禁言执行失败"
        else:
            logger.info(
                f"[LuwanPlugin] 投票未通过，不执行禁言 | 好:{good_count} 不好:{bad_count}"
            )
            result_message = (
                f"投票结束！同意票({good_count}) <= 反对票({bad_count})，不执行禁言"
            )

        try:
            await session.bot.send_group_msg(
                group_id=int(session.group_id),
                message=[
                    {"type": "reply", "data": {"id": session.message_id}},
                    {"type": "text", "data": {"text": result_message}},
                ],
            )
        except Exception as e:
            logger.warning(f"[LuwanPlugin] 发送投票结果失败: {e}")

        if vote_key in self._vote_sessions:
            del self._vote_sessions[vote_key]
