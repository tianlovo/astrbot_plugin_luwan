"""图片转发服务

定时轮询 ComuPik API，将新图片转发到配置的 QQ 群。
"""

import asyncio
import time
from pathlib import Path

from astrbot.api import logger

from ..config import LuwanConfig
from ..database import LuwanDB
from .srv_comupik_client import ComuPikClient, ImageInfo


class ImageForwarder:
    """图片转发服务

    负责定时轮询 ComuPik API 并将新图片转发到配置的 QQ 群。

    Example:
        ```python
        forwarder = ImageForwarder(config, database, context)
        await forwarder.start()
        # ... 运行中 ...
        await forwarder.stop()
        ```
    """

    def __init__(
        self,
        config: LuwanConfig,
        database: LuwanDB,
        context,
    ):
        """初始化转发服务

        Args:
            config: 插件配置
            database: 数据库实例
            context: AstrBot 上下文
        """
        self.cfg = config
        self.db = database
        self.context = context
        self.client: ComuPikClient | None = None
        self._poll_task: asyncio.Task | None = None
        self._running = False

    async def initialize(self) -> bool:
        """初始化转发服务

        Returns:
            是否初始化成功
        """
        if not self.cfg.comupik_enabled:
            logger.info("[ImageForwarder] 图片转发功能已禁用")
            return False

        if not self.cfg.comupik_api_url:
            logger.warning("[ImageForwarder] ComuPik API 地址未配置")
            return False

        if not self.cfg.comupik_target_groups:
            logger.warning("[ImageForwarder] 目标 QQ 群列表未配置")
            return False

        try:
            self.client = ComuPikClient(self.cfg.comupik_api_url)

            # 检查 API 服务健康状态
            if not await self.client.health_check():
                logger.error(
                    f"[ImageForwarder] ComuPik API 服务不可用: {self.cfg.comupik_api_url}"
                )
                return False

            logger.info(
                f"[ImageForwarder] 初始化完成，API: {self.cfg.comupik_api_url}, "
                f"目标群: {self.cfg.comupik_target_groups}"
            )
            return True

        except Exception as e:
            logger.error(f"[ImageForwarder] 初始化失败: {e}")
            return False

    async def start(self) -> None:
        """启动转发服务"""
        if self._running:
            logger.warning("[ImageForwarder] 服务已在运行中")
            return

        if not self.client:
            logger.error("[ImageForwarder] 服务未初始化")
            return

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("[ImageForwarder] 服务已启动")

    async def stop(self) -> None:
        """停止转发服务"""
        self._running = False

        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self.client:
            await self.client.close()
            self.client = None

        logger.info("[ImageForwarder] 服务已停止")

    async def _poll_loop(self) -> None:
        """轮询循环"""
        interval = self.cfg.comupik_poll_interval
        time_range = self.cfg.comupik_poll_time_range

        logger.info(
            f"[ImageForwarder] 开始轮询，间隔: {interval}秒, 时间范围: {time_range}小时"
        )

        while self._running:
            try:
                await self._poll_and_forward(time_range)
            except Exception as e:
                logger.error(f"[ImageForwarder] 轮询出错: {e}")

            await asyncio.sleep(interval)

    async def _poll_and_forward(self, time_range_hours: int) -> None:
        """轮询并转发图片

        Args:
            time_range_hours: 轮询时间范围（小时）
        """
        if not self.client:
            return

        current_time = int(time.time())
        start_time = current_time - (time_range_hours * 3600)

        try:
            # 获取该时间范围内已转发的图片ID（防止exclude_ids膨胀）
            forwarded_ids = await self.db.get_forwarded_image_ids(
                start_time=start_time, end_time=current_time
            )

            # 获取图片列表
            images, total = await self.client.list_images(
                start_time=start_time,
                end_time=current_time,
                exclude_ids=list(forwarded_ids),
                limit=100,
            )

            if not images:
                return

            logger.info(f"[ImageForwarder] 发现 {len(images)} 张新图片 (总计 {total})")

            # 转发每张图片
            for image in images:
                if not self._running:
                    break

                await self._process_image(image)

        except Exception as e:
            logger.error(f"[ImageForwarder] 获取图片列表失败: {e}")

    async def _process_image(self, image: ImageInfo) -> None:
        """处理单张图片

        Args:
            image: 图片信息
        """
        # 检查图片是否已转发
        if await self.db.is_image_forwarded(image.id):
            self.client._known_ids.add(image.id)
            return

        # 检查图片状态
        if image.status != "available":
            logger.warning(
                f"[ImageForwarder] 图片 {image.id} 状态不可用: {image.status}"
            )
            self.client._known_ids.add(image.id)
            return

        # 检查 file_path 是否为本地路径
        file_path = image.file_path
        if file_path.startswith(("http://", "https://")):
            logger.warning(
                f"[ImageForwarder] 图片 {image.id} 的 file_path 是网络 URL，非本地路径，跳过处理: {file_path}"
            )
            self.client._known_ids.add(image.id)
            return

        # 双重校验：检查物理文件是否存在
        if not Path(file_path).exists():
            logger.warning(
                f"[ImageForwarder] 图片 {image.id} 的物理文件不存在，跳过处理: {file_path}"
            )
            self.client._known_ids.add(image.id)
            return

        try:
            # 转发到所有目标群（直接使用 file_path，无需下载）
            await self._forward_to_groups(image)

            # 记录已转发
            await self.db.record_forwarded_image(image.id)
            self.client._known_ids.add(image.id)

            logger.info(f"[ImageForwarder] 图片 {image.id} 转发完成")

        except Exception as e:
            logger.error(f"[ImageForwarder] 处理图片 {image.id} 失败: {e}")

    async def _forward_to_groups(self, image: ImageInfo) -> None:
        """转发图片到所有目标群

        Args:
            image: 图片信息
        """
        from astrbot.api.event import MessageChain
        from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_platform_adapter import (
            AiocqhttpAdapter,
        )
        from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType

        # 获取 aiocqhttp 平台适配器
        platform = self.context.get_platform(PlatformAdapterType.AIOCQHTTP)
        if not platform:
            logger.error("[ImageForwarder] 无法获取 aiocqhttp 平台适配器")
            return

        # 判断是否为 AiocqhttpAdapter 实例
        if not isinstance(platform, AiocqhttpAdapter):
            logger.error(f"[ImageForwarder] 平台适配器类型不匹配: {type(platform)}")
            return

        # 获取平台 ID
        platform_id = platform.metadata.id
        logger.info(f"[ImageForwarder] 使用平台适配器: {platform_id}")

        # 构建消息链 - 仅发送图片
        chain = MessageChain().file_image(image.file_path)

        # 转发到每个目标群
        for group_id in self.cfg.comupik_target_groups:
            try:
                # 构建 unified_msg_origin
                umo = f"{platform_id}:GroupMessage:{group_id}"

                # 使用 context.send_message 发送主动消息
                await self.context.send_message(umo, chain)
                logger.info(f"[ImageForwarder] 已转发图片 {image.id} 到群 {group_id}")

            except Exception as e:
                logger.error(
                    f"[ImageForwarder] 转发图片 {image.id} 到群 {group_id} 失败: {e}"
                )

    def is_running(self) -> bool:
        """检查服务是否正在运行

        Returns:
            是否正在运行
        """
        return self._running and self._poll_task is not None
