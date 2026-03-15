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
    "1.2.5",
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

    # ==================== 头衔管理指令 ====================

    @filter.command("头衔", alias={"申请头衔", "我要头衔", "换头衔", "更换头衔"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def manage_title(self, event: AiocqhttpMessageEvent) -> None:
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
                event.stop_event()
                return

            # 检查是否为移除头衔操作
            if title in ("无", "取消", "移除", "删除", "off", "none"):
                async for _ in self.title_handler.handle_remove_title(event):
                    pass
            else:
                async for _ in self.title_handler.handle_apply_title(event, title):
                    pass

            # 停止事件传播
            event.stop_event()
        except Exception as e:
            logger.error(f"[LuwanPlugin] 处理头衔管理失败: {e}")
            await event.send(event.plain_result("❌ 操作失败，请稍后重试"))

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

    @filter.command("清空限制", alias={"重置限制", "清除限制"})
    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def clear_rate_limit(self, event: AiocqhttpMessageEvent) -> None:
        """清空申请限制（超级管理员专用）

        指令: 清空限制 [QQ号]
        别名: 重置限制、清除限制
        示例:
          - 清空限制（清空所有用户限制）
          - 清空限制 123456789（清空指定用户限制）
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
            parts = message_str.split(maxsplit=1)

            if len(parts) >= 2:
                # 清空指定用户的限制
                target_user_id = parts[1].strip()
                success = await self.db.clear_rate_limit(target_user_id)
                if success:
                    await event.send(
                        event.plain_result(f"✅ 已清空用户 {target_user_id} 的申请限制")
                    )
                else:
                    await event.send(event.plain_result("❌ 清空限制失败"))
            else:
                # 清空所有用户的限制
                success = await self.db.clear_rate_limit()
                if success:
                    await event.send(event.plain_result("✅ 已清空所有用户的申请限制"))
                else:
                    await event.send(event.plain_result("❌ 清空限制失败"))

            event.stop_event()
        except Exception as e:
            logger.error(f"[LuwanPlugin] 清空限制失败: {e}")
            await event.send(event.plain_result("❌ 操作失败，请稍后重试"))

    async def terminate(self) -> None:
        """插件卸载时清理资源"""
        try:
            await self.db.close()
            logger.info("[LuwanPlugin] 插件已卸载，资源已清理")
        except Exception as e:
            logger.error(f"[LuwanPlugin] 插件卸载时出错: {e}")
