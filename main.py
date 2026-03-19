"""鹿丸插件主模块

AstrBot 群聊插件，提供帮助菜单、头衔申请与转发、管理配置等功能
"""

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)
from astrbot.core.star.filter.event_message_type import EventMessageType

from .command import HelpHandler, TestHandler, TitleHandler
from .infra import LuwanConfig, LuwanDB, Messages
from .service import GroupCheckinService, ImageForwarder, PokeService


@register(
    "astrbot_plugin_luwan",
    "Luwan",
    "AstrBot 群聊插件，提供帮助菜单、头衔申请与转发、管理配置等功能",
    "1.7.1",
)
class LuwanPlugin(Star):
    """鹿丸插件主类

    整合所有功能模块，提供群聊交互、头衔申请、管理配置等功能
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        """初始化插件

        Args:
            context: 插件上下文
            config: 插件配置
        """
        super().__init__(context)
        self.context = context
        self.cfg = LuwanConfig(config, context)
        self.db = LuwanDB(self.cfg.db_path)
        self.help_handler = HelpHandler(self.cfg.min_interval, self.cfg.daily_limit)
        self.title_handler: TitleHandler | None = None
        self.image_forwarder: ImageForwarder | None = None
        self.group_checkin: GroupCheckinService | None = None
        self.test_handler: TestHandler | None = None
        self.poke_service: PokeService | None = None

    async def initialize(self) -> None:
        """异步初始化插件"""
        try:
            await self.db.init()
            self.title_handler = TitleHandler(self.cfg, self.db)
            self.test_handler = TestHandler(self.cfg, self.context)
            self.poke_service = PokeService(self.cfg, self.db, self.context)

            # 初始化 ComuPik 图片转发服务
            await self.db.init_comupik_tables()
            self.image_forwarder = ImageForwarder(self.cfg, self.db, self.context)
            if await self.image_forwarder.initialize():
                await self.image_forwarder.start()

            # 初始化群打卡服务
            await self.db.init_group_checkin_tables()
            self.group_checkin = GroupCheckinService(self.cfg, self.db, self.context)
            if await self.group_checkin.initialize():
                await self.group_checkin.start()

            logger.info("[LuwanPlugin] 插件初始化完成")
        except Exception as e:
            logger.error(f"[LuwanPlugin] 插件初始化失败: {e}")
            raise

    # ==================== 帮助菜单指令 ====================

    @filter.command("菜单", alias={"帮助", "help"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def show_menu(self, event: AiocqhttpMessageEvent) -> None:
        """显示帮助菜单

        指令: 菜单 / 帮助 / help
        显示插件的帮助信息和使用说明
        普通用户显示精简版，管理员显示完整版（含管理指令）
        """
        try:
            user_id = event.get_sender_id()
            is_admin = self.cfg.is_admin(user_id)
            await self.help_handler.show_menu(event, is_admin)
        except Exception as e:
            logger.error(f"[LuwanPlugin] 显示帮助菜单失败: {e}")
            await event.send(
                event.plain_result(Messages.get("common.error.operation_failed"))
            )

    # ==================== 头衔管理指令 ====================

    @filter.command("头衔", alias={"申请头衔", "我要头衔", "换头衔", "更换头衔"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def manage_title(self, event: AiocqhttpMessageEvent):
        """管理群头衔（申请/更换/移除）

        指令: 头衔 <头衔名称>
        别名: 申请头衔、我要头衔、换头衔、更换头衔
        示例:
          - 头衔 小可爱（申请/更换头衔）
          - 头衔 无（移除头衔）
          - 头衔 取消（移除头衔）
        """
        if not self.title_handler:
            await event.send(
                event.plain_result(Messages.get("common.error.operation_failed"))
            )
            return

        try:
            # 提取头衔名称
            message_str = event.message_str
            title = self.title_handler.extract_title_from_message(message_str, "头衔")

            if title is None:
                # 尝试其他别名
                for cmd in ["申请头衔", "我要头衔", "换头衔", "更换头衔"]:
                    title = self.title_handler.extract_title_from_message(
                        message_str, cmd
                    )
                    if title is not None:
                        break

            if title is None:
                await event.send(
                    event.plain_result(
                        Messages.get("title.error.no_name")
                        + "\n"
                        + Messages.get("title.hint.usage")
                    )
                )
                return

            # 检查是否为移除头衔操作
            if title in ("无", "取消", "移除", "删除", "off", "none"):
                await self.title_handler.handle_remove_title(event)
            else:
                await self.title_handler.handle_apply_title(event, title)
        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理头衔管理失败: {e}")
            await event.send(
                event.plain_result(Messages.get("title.error.operation_failed"))
            )

    # ==================== 群打卡指令 ====================

    @filter.command("打卡")
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def handle_checkin(self, event: AiocqhttpMessageEvent) -> None:
        """处理群打卡命令

        指令: 打卡
        功能: 让机器人在当前群打卡
        示例:
          - @机器人 打卡（在当前群打卡）
          - @机器人 打卡 状态（仅超级管理员，显示打卡状态）
        """
        if not self.group_checkin:
            await event.send(
                event.plain_result(Messages.get("checkin.error.not_initialized"))
            )
            return

        try:
            # 获取消息内容
            message_str = event.message_str.strip()
            user_id = event.get_sender_id()
            group_id = event.get_group_id()

            # 检查是否是状态查询命令
            if "状态" in message_str or "status" in message_str.lower():
                # 仅超级管理员可使用
                if not self.cfg.is_admin(user_id):
                    await event.send(
                        event.plain_result(Messages.get("checkin.error.not_admin"))
                    )
                    return
                await self._show_checkin_status(event, group_id)
                return

            # 执行打卡
            await self._do_manual_checkin(event, group_id)

        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理打卡命令失败: {e}")
            await event.send(
                event.plain_result(Messages.get("checkin.error.checkin_failed"))
            )

    async def _do_manual_checkin(
        self, event: AiocqhttpMessageEvent, group_id: str
    ) -> None:
        """执行手动打卡

        Args:
            event: 消息事件对象
            group_id: 群号
        """
        try:
            # 检查群是否在打卡列表中
            if group_id not in self.cfg.group_checkin_target_groups:
                await event.send(
                    event.plain_result(Messages.get("checkin.error.not_in_list"))
                )
                return

            # 检查今天是否已经打卡
            already_checkin = await self.db.is_group_checked_in_today(group_id)
            if already_checkin:
                await event.send(
                    event.plain_result(Messages.get("checkin.success.already_done"))
                )
                return

            # 执行打卡
            if self.group_checkin and self.group_checkin._bot_instance:
                success = await self.group_checkin._do_checkin(
                    group_id, checkin_type="manual"
                )
                if success:
                    await event.send(
                        event.plain_result(
                            Messages.get("checkin.success.checkin_success")
                        )
                    )
                else:
                    await event.send(
                        event.plain_result(
                            Messages.get("checkin.error.permission_denied")
                        )
                    )
            else:
                await event.send(
                    event.plain_result(Messages.get("checkin.error.bot_not_ready"))
                )

        except Exception as e:
            logger.error(f"[LuwanPlugin] 手动打卡失败: {e}")
            await event.send(
                event.plain_result(Messages.get("checkin.error.checkin_failed"))
            )

    async def _show_checkin_status(
        self, event: AiocqhttpMessageEvent, group_id: str
    ) -> None:
        """显示打卡状态（仅超级管理员）

        Args:
            event: 消息事件对象
            group_id: 群号
        """
        try:
            # 获取配置信息
            timezone = self.cfg.group_checkin_timezone
            start_time = self.cfg.group_checkin_start_time
            end_time = self.cfg.group_checkin_end_time
            desire = self.cfg.group_checkin_desire
            enable_guarantee = self.cfg.group_checkin_enable_guarantee
            guarantee_time = self.cfg.group_checkin_guarantee_check_time

            # 获取当前群状态
            in_list = group_id in self.cfg.group_checkin_target_groups
            already_checkin = (
                await self.db.is_group_checked_in_today(group_id) if in_list else False
            )

            # 获取计划打卡时间
            scheduled_time = "未安排"
            if (
                in_list
                and self.group_checkin
                and group_id in self.group_checkin._scheduled_times
            ):
                scheduled_time = self.group_checkin._scheduled_times[group_id]

            # 构建状态消息
            status_text = (
                Messages.get("checkin.status.already_checked")
                if already_checkin
                else Messages.get("checkin.status.not_checked")
            )
            in_list_text = (
                Messages.get("checkin.status.in_list_yes")
                if in_list
                else Messages.get("checkin.status.in_list_no")
            )
            guarantee_text = (
                Messages.get("checkin.status.guarantee_enabled")
                if enable_guarantee
                else Messages.get("checkin.status.guarantee_disabled")
            )
            divider = Messages.get("common.divider")

            message = (
                f"{Messages.get('checkin.status.title')}\n"
                f"{divider}\n"
                f"{Messages.get('checkin.status.group_id', group_id=group_id)}\n"
                f"{Messages.get('checkin.status.in_list', in_list=in_list_text)}\n"
                f"{Messages.get('checkin.status.today_status', status_text=status_text)}\n"
                f"{Messages.get('checkin.status.scheduled_time', time=scheduled_time)}\n"
                f"{divider}\n"
                f"{Messages.get('checkin.status.timezone', timezone=timezone)}\n"
                f"{Messages.get('checkin.status.time_range', start=start_time, end=end_time)}\n"
                f"{Messages.get('checkin.status.desire', desire=desire)}\n"
                f"{Messages.get('checkin.status.guarantee', status=guarantee_text)}\n"
            )

            if enable_guarantee:
                message += f"{Messages.get('checkin.status.guarantee_time', time=guarantee_time)}\n"

            message += divider

            await event.send(event.plain_result(message))

        except Exception as e:
            logger.error(f"[LuwanPlugin] 显示打卡状态失败: {e}")
            await event.send(
                event.plain_result(Messages.get("checkin.error.get_status_failed"))
            )

    # ==================== 测试指令 ====================

    @filter.command("测试")
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def handle_test(self, event: AiocqhttpMessageEvent) -> None:
        """测试命令（仅超级管理员可用）"""
        if self.test_handler:
            await self.test_handler.handle_test(event)
        else:
            await event.send(event.plain_result("❌ 测试功能未初始化"))

    # ==================== Bot实例捕获 ====================

    @filter.event_message_type(EventMessageType.ALL)
    async def _capture_bot_instance(self, event: AiocqhttpMessageEvent) -> None:
        """捕获Bot实例用于群打卡

        监听所有消息事件，捕获aiocqhttp平台的bot实例
        """
        try:
            if (
                self.group_checkin
                and event.get_platform_name() == "aiocqhttp"
                and isinstance(event, AiocqhttpMessageEvent)
            ):
                if event.bot and not self.group_checkin._bot_instance:
                    self.group_checkin.set_bot_instance(event.bot)

            if (
                self.poke_service
                and event.get_platform_name() == "aiocqhttp"
                and isinstance(event, AiocqhttpMessageEvent)
            ):
                if event.bot and not self.poke_service._bot_instance:
                    self.poke_service.set_bot_instance(event.bot)

            if (
                self.test_handler
                and event.get_platform_name() == "aiocqhttp"
                and isinstance(event, AiocqhttpMessageEvent)
            ):
                await self.test_handler.analyze_message(event)

            if (
                self.poke_service
                and event.get_platform_name() == "aiocqhttp"
                and isinstance(event, AiocqhttpMessageEvent)
            ):
                group_id = event.get_group_id()
                user_id = event.get_sender_id()
                message_text = event.message_str
                if group_id and user_id:
                    await self.poke_service.on_group_message(
                        group_id, user_id, message_text
                    )

                msg = getattr(event, "message_obj", None)
                raw = getattr(msg, "raw_message", None) if msg else None
                if isinstance(raw, dict) and raw.get("post_type") == "notice":
                    if (
                        raw.get("notice_type") == "notify"
                        and raw.get("sub_type") == "poke"
                    ):
                        await self.poke_service.handle_poke_event(event)
        except Exception as e:
            logger.debug(f"[LuwanPlugin] 捕获Bot实例失败: {e}")

    async def terminate(self) -> None:
        """插件卸载时清理资源"""
        try:
            # 停止图片转发服务
            if self.image_forwarder:
                await self.image_forwarder.stop()

            # 停止群打卡服务
            if self.group_checkin:
                await self.group_checkin.stop()

            await self.db.close()
            logger.info("[LuwanPlugin] 插件已卸载，资源已清理")
        except Exception as e:
            logger.error(f"[LuwanPlugin] 插件卸载时出错: {e}")
