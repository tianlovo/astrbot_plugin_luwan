# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [v1.1.2] - 2025-03-15

### Added

- feat(title_handler): 添加移除头衔功能
- feat(title_handler): 支持通过"无/取消/移除/删除/off/none"移除头衔
- feat(main): 合并申请头衔和更换头衔为统一的头衔管理指令

### Changed

- refactor(main): 将 apply_title 和 change_title 合并为 manage_title
- refactor(help_handler): 更新帮助菜单，合并头衔相关指令为"头衔管理"

## [v1.1.1] - 2025-03-15

### Added

- feat(title_handler): 添加头衔格式验证功能
- feat(title_handler): 头衔不可包含空格（半角和全角）
- feat(title_handler): 头衔长度限制为最多5个字符

## [v1.1.0] - 2025-03-15

### Added

- feat(help_handler): 普通用户显示精简版帮助菜单
- feat(help_handler): 管理员显示完整版帮助菜单（含管理指令）
- feat(title_handler): 额外发送头衔内容消息，方便群主复制
- feat(main): 根据用户权限显示对应版本的帮助菜单

### Changed

- refactor(help_handler): 分离普通用户和管理员帮助菜单
- refactor(title_handler): 移除转发消息中的"如需批准"提示
- refactor(help_handler): 精简帮助菜单内容，移除插件名称

### Removed

- 帮助菜单中的"鹿丸插件"标题
- 普通用户帮助菜单中的管理员指令部分
- 转发消息中的批准提示和操作指引

## [v1.0.0] - 2025-03-15

### Added

- feat: 实现鹿丸插件核心功能
- feat: 添加帮助菜单指令（菜单/帮助/help）
- feat: 实现头衔申请功能，支持申请头衔和更换头衔
- feat: 实现防骚扰机制，包含冷却时间和每日申请次数限制
- feat: 实现申请信息自动转发至群主私聊
- feat: 添加管理配置指令，支持查看和修改配置
- feat: 集成 WebUI 可视化配置，通过 _conf_schema.json 定义配置项
- feat: 添加 SQLite 数据库支持，持久化存储申请记录和频率限制数据
- docs: 完善 README.md 使用文档

### Features

- 群聊交互功能：响应用户的"菜单"或"帮助"指令
- 头衔申请功能：支持用户申请和更换群头衔
- 防骚扰机制：限制申请频率和每日次数
- 管理配置功能：支持指令和 WebUI 两种配置方式
