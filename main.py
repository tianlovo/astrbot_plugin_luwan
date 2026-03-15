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
from .help_handler import HelpHandler
from .title_handler import TitleHandler


@register(
    "astrbot_plugin_luwan",
    "Luwan",
    "AstrBot 群聊插件，提供帮助菜单、头衔申请与转发、管理配置等功能",
    "1.1.0",
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

    async def initialize(self) -> None:
        """异步初始化插件"""
        try:
            await self.db.init()
            self.title_handler = TitleHandler(self.cfg, self.db)
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

    # ==================== 头衔申请指令 ====================

    @filter.command("申请头衔", alias={"我要头衔"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def apply_title(self, event: AiocqhttpMessageEvent) -> None:
        """申请群头衔

        指令: 申请头衔 <头衔名称>
        别名: 我要头衔
        示例: 申请头衔 小可爱
        """
        if not self.title_handler:
            await event.send(event.plain_result("❌ 插件尚未初始化完成，请稍后重试"))
            return

        try:
            # 提取头衔名称
            message_str = event.message_str
            title = self.title_handler.extract_title_from_message(
                message_str, "申请头衔"
            )

            if not title:
                # 尝试别名"我要头衔"
                title = self.title_handler.extract_title_from_message(
                    message_str, "我要头衔"
                )

            if not title:
                await event.send(
                    event.plain_result(
                        "❌ 请输入要申请的头衔名称\n示例：申请头衔 小可爱"
                    )
                )
                event.stop_event()
                return

            await self.title_handler.handle_apply_title(event, title)
        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理头衔申请失败: {e}")
            await event.send(event.plain_result("❌ 申请失败，请稍后重试"))

    @filter.command("换头衔", alias={"更换头衔"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def change_title(self, event: AiocqhttpMessageEvent) -> None:
        """更换群头衔

        指令: 换头衔 <新头衔名称>
        别名: 更换头衔
        示例: 换头衔 大可爱
        """
        if not self.title_handler:
            await event.send(event.plain_result("❌ 插件尚未初始化完成，请稍后重试"))
            return

        try:
            # 提取新头衔名称
            message_str = event.message_str
            title = self.title_handler.extract_title_from_message(message_str, "换头衔")

            if not title:
                # 尝试别名"更换头衔"
                title = self.title_handler.extract_title_from_message(
                    message_str, "更换头衔"
                )

            if not title:
                await event.send(
                    event.plain_result(
                        "❌ 请输入要更换的新头衔名称\n示例：换头衔 大可爱"
                    )
                )
                event.stop_event()
                return

            await self.title_handler.handle_change_title(event, title)
        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理头衔更换失败: {e}")
            await event.send(event.plain_result("❌ 更换失败，请稍后重试"))

    # ==================== 管理配置指令 ====================

    @filter.command("鹿丸配置", alias={"lw配置"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def show_config(self, event: AiocqhttpMessageEvent) -> None:
        """查看或修改插件配置

        指令: 鹿丸配置 [配置项] [值]
        别名: lw配置
        示例:
          - 鹿丸配置（查看当前配置）
          - 鹿丸配置 forward_target_qq 123456789
        """
        user_id = event.get_sender_id()

        # 检查权限
        if not self.cfg.is_admin(user_id):
            await event.send(event.plain_result("❌ 你没有权限执行此操作"))
            event.stop_event()
            return

        try:
            # 解析参数
            message_str = event.message_str.strip()
            parts = message_str.split(maxsplit=2)

            if len(parts) == 1:
                # 仅查看配置
                config_text = self._format_config()
                await event.send(event.plain_result(config_text))
            elif len(parts) >= 3:
                # 修改配置
                config_key = parts[1]
                config_value = parts[2]

                success, msg = await self._update_config(config_key, config_value)
                await event.send(event.plain_result(msg))
            else:
                await event.send(
                    event.plain_result(
                        "❌ 参数格式错误\n"
                        "用法：\n"
                        "  鹿丸配置（查看配置）\n"
                        "  鹿丸配置 <配置项> <值>（修改配置）"
                    )
                )

            event.stop_event()
        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理配置指令失败: {e}")
            await event.send(event.plain_result("❌ 操作失败，请稍后重试"))

    def _format_config(self) -> str:
        """格式化当前配置为文本

        Returns:
            配置信息文本
        """
        return (
            "⚙️ 【鹿丸插件配置】\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 转发目标QQ: {self.cfg.forward_target_qq or '未设置'}\n"
            f"🔤 指令前缀: {self.cfg.command_prefix or '无'}\n"
            f"⏱️ 最小申请间隔: {self.cfg.min_interval} 分钟\n"
            f"📊 每日申请上限: {self.cfg.daily_limit} 次\n"
            f"👤 超级管理员: {self.cfg.super_admin or '未设置'}\n"
            f"✅ 自动批准: {'开启' if self.cfg.auto_approve else '关闭'}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 修改配置: 鹿丸配置 <配置项> <值>"
        )

    async def _update_config(self, key: str, value: str) -> tuple[bool, str]:
        """更新配置项

        Args:
            key: 配置项键名
            value: 配置项值

        Returns:
            (是否成功, 提示信息)
        """
        # 允许修改的配置项
        allowed_keys = [
            "forward_target_qq",
            "command_prefix",
            "super_admin",
            "auto_approve",
        ]

        if key not in allowed_keys:
            return False, f"❌ 未知的配置项: {key}\n可配置项: {', '.join(allowed_keys)}"

        try:
            # 类型转换
            if key == "auto_approve":
                value = value.lower() in ("true", "1", "on", "开启", "是")
            elif key in ("min_interval", "daily_limit"):
                value = int(value)

            # 更新配置
            self.cfg.config[key] = value

            # 保存配置
            self.cfg.config.save_config()

            # 更新帮助菜单中的频率限制显示
            if key in ("min_interval", "daily_limit"):
                self.help_handler.update_rate_limit(
                    self.cfg.min_interval, self.cfg.daily_limit
                )

            logger.info(f"[LuwanPlugin] 配置已更新: {key} = {value}")
            return True, f"✅ 配置已更新: {key} = {value}"
        except ValueError:
            return False, f"❌ 配置值类型错误: {key}"
        except Exception as e:
            logger.error(f"[LuwanPlugin] 更新配置失败: {e}")
            return False, f"❌ 更新配置失败: {e}"

    async def terminate(self) -> None:
        """插件卸载时清理资源"""
        try:
            await self.db.close()
            logger.info("[LuwanPlugin] 插件已卸载，资源已清理")
        except Exception as e:
            logger.error(f"[LuwanPlugin] 插件卸载时出错: {e}")
