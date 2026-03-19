"""数据库管理模块

提供头衔申请记录和频率限制数据的持久化存储
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

from astrbot.api import logger


class LuwanDB:
    """鹿丸插件数据库类

    管理头衔申请记录和用户频率限制数据
    """

    def __init__(self, db_path: Path):
        """初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def init(self) -> None:
        """异步初始化数据库

        创建必要的表结构
        """
        async with self._init_lock:
            if self._initialized:
                return

            # 确保目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # 连接数据库
            self._conn = await aiosqlite.connect(str(self.db_path))
            self._conn.row_factory = aiosqlite.Row

            # 创建头衔申请表
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS title_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    apply_time INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    UNIQUE(user_id, group_id, title)
                )
            """)

            # 创建频率限制记录表
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_records (
                    user_id TEXT PRIMARY KEY,
                    last_apply_time INTEGER NOT NULL,
                    daily_count INTEGER DEFAULT 1,
                    date TEXT NOT NULL
                )
            """)

            await self._conn.commit()
            self._initialized = True
            logger.info(f"[LuwanDB] 数据库初始化完成: {self.db_path}")

    async def add_application(self, user_id: str, group_id: str, title: str) -> bool:
        """添加头衔申请记录

        Args:
            user_id: 申请人 QQ 号
            group_id: 群号
            title: 申请的头衔

        Returns:
            是否添加成功
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO title_applications
                (user_id, group_id, title, apply_time, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (user_id, group_id, title, int(datetime.now().timestamp())),
            )
            await self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"[LuwanDB] 添加申请记录失败: {e}")
            return False

    async def get_user_applications(
        self, user_id: str, group_id: str | None = None
    ) -> list[dict]:
        """获取用户的申请记录

        Args:
            user_id: 用户 QQ 号
            group_id: 可选的群号过滤

        Returns:
            申请记录列表
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        if group_id:
            async with self._conn.execute(
                """
                SELECT * FROM title_applications
                WHERE user_id = ? AND group_id = ?
                ORDER BY apply_time DESC
                """,
                (user_id, group_id),
            ) as cursor:
                rows = await cursor.fetchall()
        else:
            async with self._conn.execute(
                """
                SELECT * FROM title_applications
                WHERE user_id = ?
                ORDER BY apply_time DESC
                """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def update_application_status(
        self, user_id: str, group_id: str, title: str, status: str
    ) -> bool:
        """更新申请状态

        Args:
            user_id: 申请人 QQ 号
            group_id: 群号
            title: 头衔
            status: 新状态 (pending/approved/rejected)

        Returns:
            是否更新成功
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            await self._conn.execute(
                """
                UPDATE title_applications
                SET status = ?
                WHERE user_id = ? AND group_id = ? AND title = ?
                """,
                (status, user_id, group_id, title),
            )
            await self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"[LuwanDB] 更新申请状态失败: {e}")
            return False

    async def check_rate_limit(
        self, user_id: str, min_interval: int, daily_limit: int
    ) -> tuple[bool, str]:
        """检查用户是否触发频率限制

        Args:
            user_id: 用户 QQ 号
            min_interval: 最小申请间隔（分钟）
            daily_limit: 每日申请次数上限

        Returns:
            (是否通过检查, 提示信息)
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 获取用户记录
        async with self._conn.execute(
            "SELECT * FROM rate_limit_records WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            # 新用户，允许申请
            return True, ""

        record = dict(row)
        last_apply_time = datetime.fromtimestamp(record["last_apply_time"])
        daily_count = record["daily_count"]
        record_date = record["date"]

        # 检查是否是新的一天
        if record_date != today:
            # 重置计数
            await self._reset_daily_count(user_id)
            return True, ""

        # 检查冷却时间
        time_diff = now - last_apply_time
        if time_diff < timedelta(minutes=min_interval):
            wait_minutes = min_interval - int(time_diff.total_seconds() / 60)
            return False, f"申请太频繁啦，请等待 {wait_minutes} 分钟后再试"

        # 检查日申请次数
        if daily_count >= daily_limit:
            return False, f"今日申请次数已达上限 ({daily_limit} 次)，请明天再试"

        return True, ""

    async def record_application(self, user_id: str) -> None:
        """记录本次申请

        Args:
            user_id: 用户 QQ 号
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # 获取当前记录
        async with self._conn.execute(
            "SELECT * FROM rate_limit_records WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row and dict(row)["date"] == today:
            # 同一天，增加计数
            await self._conn.execute(
                """
                UPDATE rate_limit_records
                SET last_apply_time = ?, daily_count = daily_count + 1
                WHERE user_id = ?
                """,
                (int(now.timestamp()), user_id),
            )
        else:
            # 新用户或新的一天，创建新记录
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO rate_limit_records
                (user_id, last_apply_time, daily_count, date)
                VALUES (?, ?, 1, ?)
                """,
                (user_id, int(now.timestamp()), today),
            )

        await self._conn.commit()

    async def _reset_daily_count(self, user_id: str) -> None:
        """重置用户每日计数

        Args:
            user_id: 用户 QQ 号
        """
        if not self._conn:
            return

        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        await self._conn.execute(
            """
            INSERT OR REPLACE INTO rate_limit_records
            (user_id, last_apply_time, daily_count, date)
            VALUES (?, ?, 1, ?)
            """,
            (user_id, int(now.timestamp()), today),
        )
        await self._conn.commit()

    async def clear_rate_limit(self, user_id: str | None = None) -> bool:
        """清空申请限制

        Args:
            user_id: 用户 QQ 号，如果为 None 则清空所有用户的限制

        Returns:
            是否清空成功
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            if user_id:
                # 清空指定用户的限制
                await self._conn.execute(
                    "DELETE FROM rate_limit_records WHERE user_id = ?",
                    (user_id,),
                )
                logger.info(f"[LuwanDB] 已清空用户 {user_id} 的申请限制")
            else:
                # 清空所有用户的限制
                await self._conn.execute("DELETE FROM rate_limit_records")
                logger.info("[LuwanDB] 已清空所有用户的申请限制")

            await self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"[LuwanDB] 清空申请限制失败: {e}")
            return False

    # ==================== ComuPik 图片转发记录 ====================

    async def init_comupik_tables(self) -> None:
        """初始化 ComuPik 相关数据库表"""
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            # 创建已转发图片记录表
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS comupik_forwarded_images (
                    image_id INTEGER PRIMARY KEY,
                    forwarded_at INTEGER NOT NULL
                )
                """
            )

            # 创建索引
            await self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_forwarded_at
                ON comupik_forwarded_images(forwarded_at)
                """
            )

            await self._conn.commit()
            logger.info("[LuwanDB] ComuPik 相关表初始化完成")
        except Exception as e:
            logger.error(f"[LuwanDB] ComuPik 表初始化失败: {e}")
            raise

    async def is_image_forwarded(self, image_id: int) -> bool:
        """检查图片是否已转发

        Args:
            image_id: 图片ID

        Returns:
            是否已转发
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            async with self._conn.execute(
                "SELECT 1 FROM comupik_forwarded_images WHERE image_id = ?",
                (image_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
        except Exception as e:
            logger.error(f"[LuwanDB] 检查图片转发状态失败: {e}")
            return False

    async def record_forwarded_image(self, image_id: int) -> bool:
        """记录已转发的图片

        Args:
            image_id: 图片ID

        Returns:
            是否记录成功
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            now = int(time.time())
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO comupik_forwarded_images
                (image_id, forwarded_at)
                VALUES (?, ?)
                """,
                (image_id, now),
            )
            await self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"[LuwanDB] 记录图片转发状态失败: {e}")
            return False

    async def get_forwarded_image_ids(
        self, start_time: int | None = None, end_time: int | None = None
    ) -> set[int]:
        """获取已转发的图片ID

        Args:
            start_time: 开始时间戳（可选）
            end_time: 结束时间戳（可选）

        Returns:
            已转发的图片ID集合
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            # 如果提供了时间范围，只获取该范围内的记录
            if start_time is not None and end_time is not None:
                async with self._conn.execute(
                    """
                    SELECT image_id FROM comupik_forwarded_images
                    WHERE forwarded_at >= ? AND forwarded_at <= ?
                    """,
                    (start_time, end_time),
                ) as cursor:
                    rows = await cursor.fetchall()
                    return {row[0] for row in rows}
            else:
                # 获取所有记录（向后兼容）
                async with self._conn.execute(
                    "SELECT image_id FROM comupik_forwarded_images"
                ) as cursor:
                    rows = await cursor.fetchall()
                    return {row[0] for row in rows}
        except Exception as e:
            logger.error(f"[LuwanDB] 获取已转发图片ID失败: {e}")
            return set()

    async def cleanup_old_forwarded_records(self, days: int = 30) -> int:
        """清理旧的转发记录

        Args:
            days: 保留多少天内的记录

        Returns:
            清理的记录数
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            cutoff_time = int(time.time()) - (days * 86400)
            async with self._conn.execute(
                "DELETE FROM comupik_forwarded_images WHERE forwarded_at < ?",
                (cutoff_time,),
            ) as cursor:
                deleted = cursor.rowcount
            await self._conn.commit()
            logger.info(f"[LuwanDB] 清理了 {deleted} 条旧的转发记录")
            return deleted
        except Exception as e:
            logger.error(f"[LuwanDB] 清理旧转发记录失败: {e}")
            return 0

    # ==================== 群打卡记录 ====================

    async def init_group_checkin_tables(self) -> None:
        """初始化群打卡相关数据库表"""
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            # 创建群打卡记录表
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS group_checkin_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    checkin_date TEXT NOT NULL,
                    checkin_time INTEGER NOT NULL,
                    checkin_type TEXT DEFAULT 'normal',
                    UNIQUE(group_id, checkin_date)
                )
                """
            )

            # 创建索引
            await self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_group_checkin_date
                ON group_checkin_records(group_id, checkin_date)
                """
            )

            await self._conn.commit()
            logger.info("[LuwanDB] 群打卡相关表初始化完成")
        except Exception as e:
            logger.error(f"[LuwanDB] 群打卡表初始化失败: {e}")
            raise

    async def is_group_checked_in_today(
        self, group_id: str, start_time: str = None
    ) -> bool:
        """检查群今天是否已经打卡

        Args:
            group_id: QQ群号
            start_time: 可选，统计开始时间 HH:MM，如 "00:00"

        Returns:
            今天是否已经打卡
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            today = datetime.now().strftime("%Y-%m-%d")

            if start_time:
                # 如果有指定开始时间，检查从该时间开始的打卡记录
                start_h, start_m = map(int, start_time.split(":"))
                start_timestamp = int(
                    datetime.now()
                    .replace(hour=start_h, minute=start_m, second=0, microsecond=0)
                    .timestamp()
                )

                async with self._conn.execute(
                    """
                    SELECT 1 FROM group_checkin_records
                    WHERE group_id = ? AND checkin_date = ? AND checkin_time >= ?
                    """,
                    (group_id, today, start_timestamp),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row is not None
            else:
                # 默认检查今天是否有打卡记录
                async with self._conn.execute(
                    "SELECT 1 FROM group_checkin_records WHERE group_id = ? AND checkin_date = ?",
                    (group_id, today),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row is not None
        except Exception as e:
            logger.error(f"[LuwanDB] 检查群打卡状态失败: {e}")
            return False

    async def record_group_checkin(
        self, group_id: str, checkin_type: str = "normal"
    ) -> bool:
        """记录群打卡

        Args:
            group_id: QQ群号
            checkin_type: 打卡类型，"normal" 或 "guarantee"

        Returns:
            是否记录成功
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            timestamp = int(now.timestamp())

            await self._conn.execute(
                """
                INSERT OR REPLACE INTO group_checkin_records
                (group_id, checkin_date, checkin_time, checkin_type)
                VALUES (?, ?, ?, ?)
                """,
                (group_id, today, timestamp, checkin_type),
            )
            await self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"[LuwanDB] 记录群打卡失败: {e}")
            return False

    async def get_group_checkin_history(
        self, group_id: str, days: int = 7
    ) -> list[dict]:
        """获取群打卡历史

        Args:
            group_id: QQ群号
            days: 查询最近多少天

        Returns:
            打卡记录列表
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            async with self._conn.execute(
                """
                SELECT * FROM group_checkin_records
                WHERE group_id = ? AND checkin_date >= ?
                ORDER BY checkin_date DESC
                """,
                (group_id, cutoff_date),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[LuwanDB] 获取群打卡历史失败: {e}")
            return []

    async def cleanup_old_checkin_records(self, days: int = 30) -> int:
        """清理旧的打卡记录

        Args:
            days: 保留多少天内的记录

        Returns:
            清理的记录数
        """
        if not self._conn:
            raise RuntimeError("数据库未初始化")

        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            async with self._conn.execute(
                "DELETE FROM group_checkin_records WHERE checkin_date < ?",
                (cutoff_date,),
            ) as cursor:
                deleted = cursor.rowcount
            await self._conn.commit()
            logger.info(f"[LuwanDB] 清理了 {deleted} 条旧的打卡记录")
            return deleted
        except Exception as e:
            logger.error(f"[LuwanDB] 清理旧打卡记录失败: {e}")
            return 0

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False
            logger.info("[LuwanDB] 数据库连接已关闭")
