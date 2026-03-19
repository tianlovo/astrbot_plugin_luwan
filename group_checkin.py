"""群打卡服务

定时检查并使用QQ群官方打卡功能（send_group_sign）打卡到配置的QQ群，
支持时间段配置、概率控制和打卡保底功能。
"""

import asyncio
import random
from datetime import datetime

from astrbot.api import logger
from astrbot.api.event import MessageChain

from .config import LuwanConfig
from .database import LuwanDB


class GroupCheckinService:
    """群打卡服务

    负责在配置的时间段内使用QQ群官方打卡功能随机打卡到指定的QQ群。
    每个群每天在时间段内随机挑选一个时间点打卡一次，失败可重试3次。
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
        self._scheduled_times: dict[
            str, str
        ] = {}  # 每个群的计划打卡时间 {group_id: HH:MM}
        self._checkin_attempts: dict[
            str, int
        ] = {}  # 每个群的尝试次数 {group_id: count}
        self._checkin_failed: dict[
            str, bool
        ] = {}  # 每个群的失败状态 {group_id: True/False}
        self._used_times: dict[
            str, set[str]
        ] = {}  # 每个群已使用过的打卡时间 {group_id: {HH:MM, ...}}
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

        if not self.cfg.group_checkin_target_groups:
            logger.warning("[GroupCheckin] 打卡群列表未配置")
            return False

        # 重置状态
        self._guarantee_checked_today = False
        self._scheduled_times = {}
        self._checkin_attempts = {}
        self._checkin_failed = {}
        # 注意：_used_times 不在此处重置，用于跨天记录历史时间

        # 为每个群生成随机的打卡时间点（确保与历史不同）
        await self._generate_scheduled_times()

        logger.info(
            f"[GroupCheckin] 初始化完成，"
            f"共 {len(self.cfg.group_checkin_target_groups)} 个群，"
            f"时间段: {self.cfg.group_checkin_start_time}-{self.cfg.group_checkin_end_time}，"
            f"欲望: {self.cfg.group_checkin_desire}%，"
            f"保底功能: {'开启' if self.cfg.group_checkin_enable_guarantee else '关闭'}"
        )
        return True

    async def _generate_scheduled_times(self) -> None:
        """为每个群生成随机的打卡时间点（确保与历史不同）"""
        start_time = self.cfg.group_checkin_start_time
        end_time = self.cfg.group_checkin_end_time

        start_h, start_m = map(int, start_time.split(":"))
        end_h, end_m = map(int, end_time.split(":"))

        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # 计算时间段内有多少个可能的分钟点
        total_minutes = end_minutes - start_minutes + 1

        for group_id in self.cfg.group_checkin_target_groups:
            if not group_id:
                continue

            # 获取该群已使用过的时间
            if group_id not in self._used_times:
                self._used_times[group_id] = set()
            used_times = self._used_times[group_id]

            # 生成可用的时间点列表（排除已使用的）
            available_times = []
            for minutes in range(start_minutes, end_minutes + 1):
                h = minutes // 60
                m = minutes % 60
                time_str = f"{h:02d}:{m:02d}"
                if time_str not in used_times:
                    available_times.append(time_str)

            # 如果所有时间都用完了，清空历史重新开始
            if not available_times:
                logger.warning(
                    f"[GroupCheckin] 群 {group_id} 所有时间点都已使用，清空历史重新开始"
                )
                used_times.clear()
                available_times = []
                for minutes in range(start_minutes, end_minutes + 1):
                    h = minutes // 60
                    m = minutes % 60
                    time_str = f"{h:02d}:{m:02d}"
                    available_times.append(time_str)

            # 随机选择一个可用时间
            scheduled_time = random.choice(available_times)

            # 记录为已使用
            used_times.add(scheduled_time)

            self._scheduled_times[group_id] = scheduled_time
            self._checkin_attempts[group_id] = 0
            self._checkin_failed[group_id] = False

            logger.info(
                f"[GroupCheckin] 群 {group_id} 计划打卡时间: {scheduled_time} "
                f"(已使用 {len(used_times)}/{total_minutes} 个时间点)"
            )

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
        # 每分钟检查一次
        interval_seconds = 60

        logger.info("[GroupCheckin] 开始检查循环，每分钟检查一次")

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

        # 检查是否需要重置状态（新的一天）
        if not hasattr(self, "_last_check_date") or self._last_check_date != today:
            self._guarantee_checked_today = False
            self._scheduled_times = {}
            self._checkin_attempts = {}
            self._checkin_failed = {}
            await self._generate_scheduled_times()
            self._last_check_date = today

        for group_id in self.cfg.group_checkin_target_groups:
            if not group_id:
                continue

            # 检查今天是否已经打卡成功
            if await self.db.is_group_checked_in_today(group_id):
                continue

            # 检查是否已经失败3次
            if self._checkin_failed.get(group_id, False):
                continue

            # 检查是否需要执行保底打卡
            is_guarantee = await self._should_guarantee_checkin(current_time, group_id)

            if is_guarantee:
                # 保底打卡：无视欲望值和时间点，强制打卡
                logger.info(f"[GroupCheckin] 群 {group_id} 触发保底打卡")
                await self._try_checkin(group_id, checkin_type="guarantee")
            else:
                # 正常打卡：检查是否到达计划时间
                scheduled_time = self._scheduled_times.get(group_id)
                if scheduled_time and current_time == scheduled_time:
                    # 根据欲望概率决定是否打卡
                    desire = self.cfg.group_checkin_desire
                    if random.randint(1, 100) <= desire:
                        await self._try_checkin(group_id, checkin_type="normal")
                    else:
                        logger.info(
                            f"[GroupCheckin] 群 {group_id} 欲望未触发，跳过打卡 (desire: {desire})"
                        )
                        # 欲望未触发，视为已处理，不再打卡
                        await self.db.record_group_checkin(
                            group_id, checkin_type="skipped"
                        )

    async def _try_checkin(self, group_id: str, checkin_type: str = "normal") -> None:
        """尝试打卡，失败可重试

        Args:
            group_id: QQ群号
            checkin_type: 打卡类型
        """
        max_retries = 3
        attempt = self._checkin_attempts.get(group_id, 0)

        if attempt >= max_retries:
            logger.warning(
                f"[GroupCheckin] 群 {group_id} 已尝试{max_retries}次，不再重试"
            )
            return

        # 执行打卡
        success = await self._do_checkin(group_id, checkin_type=checkin_type)

        if success:
            # 打卡成功
            self._checkin_attempts[group_id] = attempt + 1
            logger.info(f"[GroupCheckin] 群 {group_id} 打卡成功")
        else:
            # 打卡失败，增加尝试次数
            attempt += 1
            self._checkin_attempts[group_id] = attempt

            if attempt >= max_retries:
                # 3次失败，标记为失败并通知管理员
                self._checkin_failed[group_id] = True
                logger.error(
                    f"[GroupCheckin] 群 {group_id} 打卡失败{max_retries}次，通知管理员"
                )
                await self._notify_admin(group_id, checkin_type)
            else:
                # 重新生成一个新的打卡时间（在剩余时间段内）
                await self._reschedule_checkin_time(group_id)
                logger.info(
                    f"[GroupCheckin] 群 {group_id} 打卡失败，"
                    f"第{attempt}次尝试，已重新安排时间"
                )

    async def _reschedule_checkin_time(self, group_id: str) -> None:
        """重新安排打卡时间

        Args:
            group_id: QQ群号
        """
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        end_time = self.cfg.group_checkin_end_time
        end_h, end_m = map(int, end_time.split(":"))
        end_minutes = end_h * 60 + end_m

        # 在当前时间之后、结束时间之前随机选择
        if current_minutes < end_minutes:
            random_minutes = random.randint(current_minutes + 1, end_minutes)
            random_h = random_minutes // 60
            random_m = random_minutes % 60
            new_time = f"{random_h:02d}:{random_m:02d}"
            self._scheduled_times[group_id] = new_time
            logger.info(f"[GroupCheckin] 群 {group_id} 重新安排打卡时间: {new_time}")

    async def _do_checkin(self, group_id: str, checkin_type: str = "normal") -> bool:
        """执行QQ群打卡

        Args:
            group_id: QQ群号
            checkin_type: 打卡类型

        Returns:
            是否打卡成功
        """
        if not self._bot_instance:
            logger.error("[GroupCheckin] Bot实例未设置，无法执行打卡")
            return False

        try:
            # 调用QQ群打卡API
            await self._bot_instance.api.call_action(
                "send_group_sign", group_id=str(group_id)
            )

            # 记录打卡
            await self.db.record_group_checkin(group_id, checkin_type=checkin_type)

            type_str = "保底" if checkin_type == "guarantee" else "正常"
            logger.info(f"[GroupCheckin] 已在群 {group_id} 完成{type_str}打卡")
            return True

        except Exception as e:
            logger.error(f"[GroupCheckin] 在群 {group_id} 打卡失败: {e}")
            return False

    async def _notify_admin(self, group_id: str, checkin_type: str) -> None:
        """通知超级管理员打卡失败

        Args:
            group_id: QQ群号
            checkin_type: 打卡类型
        """
        super_admin = self.cfg.super_admin
        if not super_admin:
            logger.warning("[GroupCheckin] 未配置超级管理员，无法通知")
            return

        try:
            # 构建通知消息
            type_str = "保底" if checkin_type == "guarantee" else "正常"
            message = (
                f"⚠️ 群打卡失败通知\n"
                f"━━━━━━━━━━━━━━\n"
                f"群号: {group_id}\n"
                f"类型: {type_str}打卡\n"
                f"状态: 连续3次打卡失败\n"
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━\n"
                f"请检查机器人状态或群权限"
            )

            # 发送私聊消息给超级管理员
            # 构建 unified_msg_origin
            platform = self.context.get_platform("aiocqhttp")
            if platform:
                platform_id = platform.metadata.id
                umo = f"{platform_id}:FriendMessage:{super_admin}"
                chain = MessageChain().plain(message)
                await self.context.send_message(umo, chain)
                logger.info(f"[GroupCheckin] 已通知超级管理员 {super_admin}")

        except Exception as e:
            logger.error(f"[GroupCheckin] 通知管理员失败: {e}")

    async def _should_guarantee_checkin(self, current_time: str, group_id: str) -> bool:
        """检查是否应该执行保底打卡

        当整个群一整天（从00:00到保底检查时间）都没有任何人（包括机器人和群成员）
        打卡的情况下，触发保底打卡。

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

        # 标记今日已执行保底检查（只检查一次）
        self._guarantee_checked_today = True

        # 检查群内今日是否有人打卡（包括机器人和其他群成员）
        has_any_checkin = await self._check_group_has_any_checkin_today(group_id)

        if has_any_checkin:
            logger.info(f"[GroupCheckin] 群 {group_id} 今日已有人打卡，跳过保底")
            return False

        logger.info(f"[GroupCheckin] 群 {group_id} 今日无人打卡，触发保底")
        return True

    async def _check_group_has_any_checkin_today(self, group_id: str) -> bool:
        """检查群内今日是否有任何人打卡（包括机器人和群成员）

        通过QQ API查询群的打卡记录，判断今天是否有人打卡。

        Args:
            group_id: QQ群号

        Returns:
            今日是否有人打卡
        """
        # 首先检查数据库中机器人是否已打卡
        guarantee_start = self.cfg.group_checkin_guarantee_start_time
        has_robot_checkin = await self.db.is_group_checked_in_today(
            group_id, start_time=guarantee_start
        )

        if has_robot_checkin:
            return True

        # 如果Bot实例已设置，尝试通过API查询群打卡记录
        if self._bot_instance:
            try:
                # 调用QQ API查询群打卡信息
                result = await self._bot_instance.api.call_action(
                    "get_group_signin_info", group_id=str(group_id)
                )

                # 如果API返回了今日打卡信息，说明有人打卡
                if result and isinstance(result, dict):
                    signin_count = result.get("signin_count", 0)
                    if signin_count > 0:
                        logger.debug(
                            f"[GroupCheckin] 群 {group_id} 今日有 {signin_count} 人打卡"
                        )
                        return True

            except Exception as e:
                # API可能不存在或调用失败，记录日志但不阻断流程
                logger.debug(f"[GroupCheckin] 查询群打卡信息失败: {e}")

        # 如果无法通过API确认，保守起见认为无人打卡
        logger.debug(f"[GroupCheckin] 无法确认群 {group_id} 打卡状态，按无人打卡处理")
        return False

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

    def is_running(self) -> bool:
        """检查服务是否正在运行

        Returns:
            是否正在运行
        """
        return self._running and self._check_task is not None
