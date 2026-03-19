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

from .config import LuwanConfig
from .database import LuwanDB
from .group_checkin import GroupCheckinService
from .help_handler import HelpHandler
from .image_forwarder import ImageForwarder
from .title_handler import TitleHandler


@register(
    "astrbot_plugin_luwan",
    "Luwan",
    "AstrBot 群聊插件，提供帮助菜单、头衔申请与转发、管理配置等功能",
    "1.5.5",
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

    async def initialize(self) -> None:
        """异步初始化插件"""
        try:
            await self.db.init()
            self.title_handler = TitleHandler(self.cfg, self.db)

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
            await event.send(event.plain_result("❌ 显示帮助菜单失败，请稍后重试"))

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
            await event.send(event.plain_result("❌ 插件尚未初始化完成，请稍后重试"))
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
                        "❌ 请输入头衔名称\n"
                        "示例：\n"
                        "  头衔 小可爱（申请/更换）\n"
                        "  头衔 无（移除头衔）"
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
            await event.send(event.plain_result("❌ 操作失败，请稍后重试"))

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
