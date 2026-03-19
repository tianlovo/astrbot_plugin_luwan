"""群打卡服务

定时检查并使用QQ群官方打卡功能（send_group_sign）打卡到配置的QQ群，
支持时间段配置、概率控制和打卡保底功能。
"""

import asyncio
import random
from datetime import datetime

from astrbot.api import logger

from .config import LuwanConfig
from .database import LuwanDB


class GroupCheckinService:
    """群打卡服务

    负责在配置的时间段内使用QQ群官方打卡功能随机打卡到指定的QQ群。
    支持打卡保底功能：当晚上特定时间群内无人打卡时自动保底打卡。

    Example:
        ```python
        service = GroupCheckinService(config, database, context)
        await service.initialize()
        await service.start()
        # ... 运行中 ...
        await service.stop()
        ```
    """

    def __init__(
        self,
        config: LuwanConfig,
        database: LuwanDB,
        context,
    ):
        """初始化打卡服务

        Args:
            config: 插件配置
            database: 数据库实例
            context: AstrBot 上下文
        """
        self.cfg = config
        self.db = database
        self.context = context
        self._bot_instance = None
        self._check_task: asyncio.Task | None = None
        self._guarantee_checked_today = False  # 今日是否已执行保底检查
        self._running = False

    def set_bot_instance(self, bot_instance) -> None:
        """设置Bot实例

        Args:
            bot_instance: aiocqhttp Bot实例
        """
        self._bot_instance = bot_instance
        logger.info("[GroupCheckin] Bot实例已设置")

    async def initialize(self) -> bool:
        """初始化打卡服务

        Returns:
            是否初始化成功
        """
        if not self.cfg.group_checkin_enabled:
            logger.info("[GroupCheckin] 群打卡功能已禁用")
            return False

        if not self.cfg.group_checkin_groups:
            logger.warning("[GroupCheckin] 打卡群列表未配置")
            return False

        # 重置保底检查状态
        self._guarantee_checked_today = False

        logger.info(
            f"[GroupCheckin] 初始化完成，"
            f"共 {len(self.cfg.group_checkin_groups)} 个群，"
            f"检查间隔: {self.cfg.group_checkin_interval}分钟，"
            f"保底功能: {'开启' if self.cfg.group_checkin_enable_guarantee else '关闭'}"
        )
        return True

    async def start(self) -> None:
        """启动打卡服务"""
        if self._running:
            logger.warning("[GroupCheckin] 服务已在运行中")
            return

        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info("[GroupCheckin] 服务已启动")

    async def stop(self) -> None:
        """停止打卡服务"""
        self._running = False

        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None

        logger.info("[GroupCheckin] 服务已停止")

    async def _check_loop(self) -> None:
        """检查循环"""
        interval_minutes = self.cfg.group_checkin_interval
        interval_seconds = interval_minutes * 60

        logger.info(f"[GroupCheckin] 开始检查循环，间隔: {interval_minutes}分钟")

        while self._running:
            try:
                await self._process_checkin()
            except Exception as e:
                logger.error(f"[GroupCheckin] 检查打卡出错: {e}")

            await asyncio.sleep(interval_seconds)

    async def _process_checkin(self) -> None:
        """处理打卡逻辑"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        # 检查是否需要重置保底检查状态（新的一天）
        if not hasattr(self, "_last_check_date") or self._last_check_date != today:
            self._guarantee_checked_today = False
            self._last_check_date = today

        for group_config in self.cfg.group_checkin_groups:
            group_id = group_config.get("group_id", "")
            start_time = group_config.get("start_time", "09:00")
            end_time = group_config.get("end_time", "23:00")
            desire = group_config.get("desire", 50)

            if not group_id:
                continue

            # 检查是否在打卡时间段内
            if not self._is_in_time_range(current_time, start_time, end_time):
                continue

            # 检查今天是否已经打卡
            if await self.db.is_group_checked_in_today(group_id):
                continue

            # 检查是否需要执行保底打卡
            is_guarantee = await self._should_guarantee_checkin(current_time, group_id)

            if is_guarantee:
                # 保底打卡：无视欲望值，强制打卡
                logger.info(f"[GroupCheckin] 群 {group_id} 触发保底打卡")
                await self._do_checkin(group_id, checkin_type="guarantee")
            else:
                # 正常打卡：根据欲望概率决定是否打卡
                if random.randint(1, 100) <= desire:
                    await self._do_checkin(group_id, checkin_type="normal")
                else:
                    logger.debug(
                        f"[GroupCheckin] 群 {group_id} 本次跳过打卡 (desire: {desire})"
                    )

    async def _should_guarantee_checkin(self, current_time: str, group_id: str) -> bool:
        """检查是否应该执行保底打卡

        Args:
            current_time: 当前时间 HH:MM
            group_id: QQ群号

        Returns:
            是否应该执行保底打卡
        """
        if not self.cfg.group_checkin_enable_guarantee:
            return False

        # 检查是否到达保底检查时间
        guarantee_check_time = self.cfg.group_checkin_guarantee_check_time
        if current_time != guarantee_check_time:
            return False

        # 检查今日是否已执行过保底检查
        if self._guarantee_checked_today:
            return False

        # 标记今日已执行保底检查
        self._guarantee_checked_today = True

        # 检查群内今日是否有人打卡（从保底统计开始时间到现在）
        guarantee_start = self.cfg.group_checkin_guarantee_start_time
        has_checkin = await self.db.is_group_checked_in_today(
            group_id, start_time=guarantee_start
        )

        if has_checkin:
            logger.info(f"[GroupCheckin] 群 {group_id} 今日已有人打卡，跳过保底")
            return False

        logger.info(f"[GroupCheckin] 群 {group_id} 今日无人打卡，触发保底")
        return True

    def _is_in_time_range(self, current: str, start: str, end: str) -> bool:
        """检查当前时间是否在时间段内

        Args:
            current: 当前时间 HH:MM
            start: 开始时间 HH:MM
            end: 结束时间 HH:MM

        Returns:
            是否在时间段内
        """
        try:
            current_h, current_m = map(int, current.split(":"))
            start_h, start_m = map(int, start.split(":"))
            end_h, end_m = map(int, end.split(":"))

            current_minutes = current_h * 60 + current_m
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            return start_minutes <= current_minutes <= end_minutes
        except ValueError:
            logger.warning(
                f"[GroupCheckin] 时间格式解析失败: {current}, {start}, {end}"
            )
            return False

    async def _do_checkin(self, group_id: str, checkin_type: str = "normal") -> None:
        """执行QQ群打卡

        Args:
            group_id: QQ群号
            checkin_type: 打卡类型，"normal" 或 "guarantee"
        """
        if not self._bot_instance:
            logger.error("[GroupCheckin] Bot实例未设置，无法执行打卡")
            return

        try:
            # 调用QQ群打卡API
            await self._bot_instance.api.call_action(
                "send_group_sign", group_id=str(group_id)
            )

            # 记录打卡
            await self.db.record_group_checkin(group_id, checkin_type=checkin_type)

            type_str = "保底" if checkin_type == "guarantee" else "正常"
            logger.info(f"[GroupCheckin] 已在群 {group_id} 完成{type_str}打卡")

        except Exception as e:
            logger.error(f"[GroupCheckin] 在群 {group_id} 打卡失败: {e}")

    def is_running(self) -> bool:
        """检查服务是否正在运行

        Returns:
            是否正在运行
        """
        return self._running and self._check_task is not None
