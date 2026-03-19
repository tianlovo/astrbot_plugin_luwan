"""戳一戳服务

基于概率模型决定是否戳一戳消息发送者的后台服务。
使用逻辑回归概率公式，综合考虑触发词、管理员身份、冷却时间、群活跃度、时间段等因素。
"""

import asyncio
import math
import random
import time
from collections import defaultdict
from datetime import datetime

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import MessageChain
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter import (
    AiocqhttpAdapter,
)
from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType

from ..infra import LuwanConfig, LuwanDB


class PokeService:
    """戳一戳服务

    基于逻辑回归概率模型，在收到群消息时决定是否戳一戳发言人。
    """

    def __init__(
        self,
        config: LuwanConfig,
        database: LuwanDB,
        context,
    ):
        """初始化戳一戳服务

        Args:
            config: 插件配置
            database: 数据库实例
            context: AstrBot 上下文
        """
        self.cfg = config
        self.db = database
        self.context = context
        self._bot_instance = None
        self._group_message_counts: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def set_bot_instance(self, bot_instance) -> None:
        """设置Bot实例

        Args:
            bot_instance: aiocqhttp Bot实例
        """
        self._bot_instance = bot_instance
        logger.info("[PokeService] Bot实例已设置")

    def is_group_enabled(self, group_id: str) -> bool:
        """检查群是否启用戳一戳功能

        Args:
            group_id: 群号

        Returns:
            是否启用
        """
        if not self.cfg.poke_enabled:
            return False
        return group_id in self.cfg.poke_enabled_groups

    def _calculate_probability(
        self,
        message_text: str,
        is_admin: bool,
        hours_since_last_poke: float,
        recent_message_count: int,
        current_hour: int,
    ) -> float:
        """计算戳一戳概率

        使用逻辑回归公式：
        p = 1 / (1 + e^-(β0 + β1*x1 + β2*x2 + β3*x3 + β4*x4 + β5*x5))

        其中：
        x1: 是否包含触发词 (0 或 1)
        x2: 是否为管理员 (0 或 1)
        x3: 距离上次戳的时间，归一化到 [0,1] (min(1, t/24))
        x4: 群活跃度 [0,1] (min(1, count/100))
        x5: 时间段 (白天 1.0, 夜晚 0.5)

        Args:
            message_text: 消息文本
            is_admin: 发送者是否为管理员
            hours_since_last_poke: 距离上次戳的小时数
            recent_message_count: 最近消息数
            current_hour: 当前小时 (0-23)

        Returns:
            戳一戳概率 [0, 1]
        """
        trigger_words = self.cfg.poke_trigger_words
        x1 = 1 if any(word in message_text for word in trigger_words) else 0
        x2 = 1 if is_admin else 0
        x3 = min(1.0, hours_since_last_poke / 24.0)
        x4 = min(1.0, recent_message_count / 100.0)
        x5 = 1.0 if 8 <= current_hour < 22 else 0.5

        z = (
            self.cfg.poke_beta0
            + self.cfg.poke_beta1 * x1
            + self.cfg.poke_beta2 * x2
            + self.cfg.poke_beta3 * x3
            + self.cfg.poke_beta4 * x4
            + self.cfg.poke_beta5 * x5
        )

        probability = 1.0 / (1.0 + math.exp(-z))
        return probability

    async def should_poke(
        self,
        group_id: str,
        user_id: str,
        message_text: str,
    ) -> bool:
        """判断是否应该戳一戳

        Args:
            group_id: 群号
            user_id: 用户ID
            message_text: 消息文本

        Returns:
            是否应该戳一戳
        """
        if not self.is_group_enabled(group_id):
            return False

        is_admin = self.cfg.is_admin(user_id)

        last_poke_time = await self.db.get_last_poke_time(user_id)
        current_time = int(datetime.now().timestamp())
        cooldown_seconds = self.cfg.poke_cooldown_hours * 3600

        if last_poke_time and (current_time - last_poke_time) < cooldown_seconds:
            hours_since = (current_time - last_poke_time) / 3600.0
            logger.debug(
                f"[PokeService] 用户 {user_id} 还在冷却中 ({hours_since:.2f} 小时)"
            )
            return False

        async with self._lock:
            if user_id in self._group_message_counts:
                self._group_message_counts[user_id] = self._group_message_counts[
                    user_id
                ][-99:]
            recent_count = len(self._group_message_counts.get(user_id, []))

        hours_since_last = (
            (current_time - last_poke_time) / 3600.0 if last_poke_time else 24.0
        )

        current_hour = datetime.now().hour
        probability = self._calculate_probability(
            message_text,
            is_admin,
            hours_since_last,
            recent_count,
            current_hour,
        )

        should_poke = random.random() < probability
        logger.debug(
            f"[PokeService] 用户 {user_id} 戳一戳概率: {probability:.4f}, 结果: {should_poke}"
        )

        return should_poke

    async def do_poke(
        self,
        group_id: str,
        user_id: str,
    ) -> bool:
        """执行戳一戳

        Args:
            group_id: 群号
            user_id: 用户ID

        Returns:
            是否戳成功
        """
        try:
            platform = self.context.get_platform(PlatformAdapterType.AIOCQHTTP)
            if not platform:
                logger.warning("[PokeService] 无法获取 aiocqhttp 平台适配器")
                return False

            if not isinstance(platform, AiocqhttpAdapter):
                logger.warning(f"[PokeService] 平台适配器类型不匹配: {type(platform)}")
                return False

            platform_id = platform.metadata.id
            chain = MessageChain()
            chain.chain.append(Comp.Poke(poke_type="126", qq=int(user_id)))

            umo = f"{platform_id}:GroupMessage:{group_id}"
            await self.context.send_message(umo, chain)

            current_time = int(datetime.now().timestamp())
            await self.db.update_last_poke_time(user_id, current_time)

            logger.info(f"[PokeService] 已戳用户 {user_id} 在群 {group_id}")
            return True

        except Exception as e:
            logger.error(f"[PokeService] 戳一戳失败: {e}")
            return False

    async def on_group_message(
        self, group_id: str, user_id: str, message_text: str
    ) -> None:
        """处理群消息

        记录消息并检查是否需要戳一戳

        Args:
            group_id: 群号
            user_id: 用户ID
            message_text: 消息文本
        """
        if not self.is_group_enabled(group_id):
            return

        async with self._lock:
            self._group_message_counts[user_id].append(time.time())

        should_poke = await self.should_poke(group_id, user_id, message_text)
        if should_poke:
            await self.do_poke(group_id, user_id)
