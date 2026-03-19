"""ComuPik API 客户端

提供 ComuPik 图片服务的 Python 客户端接口。
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import aiohttp


@dataclass
class ImageInfo:
    """图片信息数据类"""

    id: int
    message_id: str
    chat_id: str
    sender_id: str
    sender_name: str
    timestamp: int
    file_path: str
    original_url: str
    file_size: int
    width: int
    height: int
    created_at: int
    status: str


@dataclass
class StatsInfo:
    """统计信息数据类"""

    total_images: int
    total_size_bytes: int
    avg_size_bytes: int
    chat_count: int
    oldest_timestamp: int
    newest_timestamp: int


class ComuPikError(Exception):
    """ComuPik SDK 异常基类"""

    pass


class APIError(ComuPikError):
    """API 调用异常"""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(f"API Error {status_code}: {message}")


class ImageNotFoundError(ComuPikError):
    """图片不存在异常"""

    pass


class ImageExpiredError(ComuPikError):
    """图片已过期异常"""

    pass


class ComuPikClient:
    """ComuPik API 客户端

    提供便捷的接口访问 ComuPik 图片服务。

    Example:
        ```python
        client = ComuPikClient("http://127.0.0.1:8080")

        # 获取统计信息
        stats = await client.get_stats()

        # 轮询新图片
        async for image in client.poll_images(interval=30):
            await process_image(image)
        ```
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        """初始化客户端

        Args:
            base_url: API 基础 URL
        """
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._known_ids: set[int] = set()
        self._last_end_time: int = int(time.time())

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    async def close(self):
        """关闭客户端连接"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送 HTTP 请求

        Args:
            method: HTTP 方法
            path: API 路径
            **kwargs: 请求参数

        Returns:
            响应数据

        Raises:
            APIError: API 调用失败
        """
        url = f"{self.base_url}{path}"
        session = self._get_session()

        async with session.request(method, url, **kwargs) as resp:
            data = await resp.json()

            if resp.status >= 400:
                raise APIError(
                    data.get("message", "Unknown error"), status_code=resp.status
                )

            return data

    async def health_check(self) -> bool:
        """健康检查

        Returns:
            服务是否正常
        """
        try:
            data = await self._request("GET", "/api/health")
            return data.get("status") == "ok"
        except Exception:
            return False

    async def get_stats(self) -> StatsInfo:
        """获取统计信息

        Returns:
            统计信息

        Raises:
            APIError: API 调用失败
        """
        data = await self._request("GET", "/api/stats")
        stats = data["data"]
        return StatsInfo(
            total_images=stats["total_images"],
            total_size_bytes=stats["total_size_bytes"],
            avg_size_bytes=stats["avg_size_bytes"],
            chat_count=stats["chat_count"],
            oldest_timestamp=stats["oldest_timestamp"],
            newest_timestamp=stats["newest_timestamp"],
        )

    async def list_images(
        self,
        start_time: int,
        end_time: int,
        exclude_ids: list[int] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ImageInfo], int]:
        """获取图片列表

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            exclude_ids: 要排除的图片ID列表
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            (图片列表, 总数)

        Raises:
            APIError: API 调用失败
        """
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "exclude_ids": json.dumps(exclude_ids or []),
            "limit": limit,
            "offset": offset,
        }

        data = await self._request("GET", "/api/images", params=params)
        result = data["data"]

        images = [
            ImageInfo(
                id=img["id"],
                message_id=img["message_id"],
                chat_id=img["chat_id"],
                sender_id=img["sender_id"],
                sender_name=img["sender_name"],
                timestamp=img["timestamp"],
                file_path=img["file_path"],
                original_url=img["original_url"],
                file_size=img["file_size"],
                width=img["width"],
                height=img["height"],
                created_at=img["created_at"],
                status=img["status"],
            )
            for img in result["images"]
        ]

        return images, result["total"]

    async def get_image(self, image_id: int) -> ImageInfo:
        """获取单个图片信息

        Args:
            image_id: 图片ID

        Returns:
            图片信息

        Raises:
            ImageNotFoundError: 图片不存在
            APIError: API 调用失败
        """
        try:
            data = await self._request("GET", f"/api/images/{image_id}")
        except APIError as e:
            if e.status_code == 404:
                raise ImageNotFoundError(f"图片不存在: {image_id}")
            raise

        img = data["data"]
        return ImageInfo(
            id=img["id"],
            message_id=img["message_id"],
            chat_id=img["chat_id"],
            sender_id=img["sender_id"],
            sender_name=img["sender_name"],
            timestamp=img["timestamp"],
            file_path=img["file_path"],
            original_url=img["original_url"],
            file_size=img["file_size"],
            width=img["width"],
            height=img["height"],
            created_at=img["created_at"],
            status=img["status"],
        )

    async def download_image(
        self,
        filename: str,
        save_path: Path | None = None,
    ) -> bytes | None:
        """下载图片文件

        Args:
            filename: 文件名
            save_path: 保存路径（可选）

        Returns:
            图片数据，如果图片不可用返回 None

        Raises:
            ImageNotFoundError: 图片不存在
            ImageExpiredError: 图片已过期
            APIError: API 调用失败
        """
        url = f"{self.base_url}/api/file/{filename}"
        session = self._get_session()

        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                if save_path:
                    save_path.write_bytes(data)
                return data
            elif resp.status == 202:
                # 正在下载中
                return None
            elif resp.status == 404:
                raise ImageNotFoundError(f"图片不存在: {filename}")
            elif resp.status == 410:
                raise ImageExpiredError(f"图片已过期: {filename}")
            else:
                raise APIError(f"下载失败: {resp.status}", status_code=resp.status)

    async def poll_images(
        self,
        interval: int = 30,
        time_range_hours: int = 12,
        start_from: int | None = None,
    ) -> AsyncIterator[ImageInfo]:
        """轮询新图片

        持续轮询获取新图片，是一个异步生成器。

        Args:
            interval: 轮询间隔（秒）
            time_range_hours: 轮询时间范围（小时），默认12小时
            start_from: 开始时间戳（默认从当前时间减去time_range_hours开始）

        Yields:
            新图片信息

        Example:
            ```python
            async for image in client.poll_images(interval=30, time_range_hours=12):
                print(f"新图片: {image.id}")
                # 下载图片
                data = await client.download_image(
                    Path(image.file_path).name
                )
            ```
        """
        if start_from:
            self._last_end_time = start_from
        else:
            # 默认从 time_range_hours 小时前开始
            self._last_end_time = int(time.time()) - (time_range_hours * 3600)

        while True:
            current_time = int(time.time())

            try:
                images, _ = await self.list_images(
                    start_time=self._last_end_time,
                    end_time=current_time,
                    exclude_ids=list(self._known_ids),
                    limit=100,
                )

                for image in images:
                    self._known_ids.add(image.id)
                    yield image

                self._last_end_time = current_time

            except Exception as e:
                print(f"轮询出错: {e}")

            await asyncio.sleep(interval)

    def reset_poll_state(self):
        """重置轮询状态

        清除已知的图片ID和时间戳，重新开始轮询。
        """
        self._known_ids.clear()
        self._last_end_time = int(time.time())

    def set_known_ids(self, known_ids: set[int]):
        """设置已知的图片ID集合

        Args:
            known_ids: 已知的图片ID集合
        """
        self._known_ids = known_ids
