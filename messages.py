"""消息管理模块

提供统一的字符串获取接口，从 messages.json 加载消息
"""

import json
from pathlib import Path
from typing import Any


class Messages:
    """消息管理类

    提供从 JSON 文件加载消息并获取消息的接口
    """

    _instance: "Messages | None" = None
    _messages: dict[str, Any] = {}

    def __new__(cls) -> "Messages":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_messages()
        return cls._instance

    def _load_messages(self) -> None:
        """从 JSON 文件加载消息"""
        messages_path = Path(__file__).parent / "messages.json"
        try:
            with open(messages_path, encoding="utf-8") as f:
                self._messages = json.load(f)
        except Exception as e:
            print(f"[Messages] 加载消息文件失败: {e}")
            self._messages = {}

    def get(self, key: str, default: str = "", **kwargs) -> str:
        """获取消息

        Args:
            key: 消息键路径，使用点号分隔，如 "title.error.no_name"
            default: 默认值，当键不存在时返回
            **kwargs: 格式化参数

        Returns:
            消息文本

        Example:
            >>> Messages.get("title.error.no_name")
            '❌ 请输入头衔名称'
            >>> Messages.get("title.apply.success", action="申请", title="小可爱")
            '\\n✅ 已申请头衔「小可爱」\\n📢 已通知群主处理，请耐心等待'
        """
        keys = key.split(".")
        value = self._messages

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        if isinstance(value, str):
            if kwargs:
                try:
                    return value.format(**kwargs)
                except (KeyError, ValueError):
                    return value
            return value

        return default

    @classmethod
    def reload(cls) -> None:
        """重新加载消息文件"""
        if cls._instance is not None:
            cls._instance._load_messages()
