"""数据库管理模块

提供头衔申请记录和频率限制数据的持久化存储
"""

import asyncio
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

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False
            logger.info("[LuwanDB] 数据库连接已关闭")
