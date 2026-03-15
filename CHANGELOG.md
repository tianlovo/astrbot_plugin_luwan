# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [v1.2.7] - 2025-03-15

### Fixed

- fix(main): 优化生成器调用方式
- fix(main): 将 `async for _ in ...` 改为直接使用 `yield`
- fix(main): 移除 `manage_title` 方法的 `-> None` 返回类型注解

## [v1.2.6] - 2025-03-15

### Fixed

- fix: 移除多处 event.stop_event() 调用，修复消息发送问题
- fix(main): 移除 manage_title 中的 event.stop_event()
- fix(main): 移除 show_config 中的 event.stop_event()
- fix(main): 移除 clear_rate_limit 中的 event.stop_event()
- fix(help_handler): 移除 send_help 中的 event.stop_event()

## [v1.2.5] - 2025-03-15

### Fixed

- fix(title_handler): 修复消息组件导入方式
- fix(title_handler): 使用 `import astrbot.api.message_components as Comp` 导入
- fix(title_handler): 使用 `Comp.Reply`、`Comp.At`、`Comp.Plain` 构建消息链

## [v1.2.4] - 2025-03-15

### Fixed

- fix(title_handler): 修复 event.stop_event() 中断消息发送问题
- fix(title_handler): 移除 handle_apply_title 中的 event.stop_event()
- fix(title_handler): 移除 handle_remove_title 中的 event.stop_event()
- fix(main): 在生成器调用后添加 event.stop_event()

## [v1.2.3] - 2025-03-15

### Fixed

- fix(title_handler): 修复消息发送方式错误
- fix(title_handler): 将 await event.send() 改为 yield event.chain_result()
- fix(main): 适配生成器调用方式，使用 async for 迭代

## [v1.2.2] - 2025-03-15

### Fixed

- fix(title_handler): 修复 Reply 初始化参数错误
- fix(title_handler): 将 Reply(message_id) 改为 Reply(id=message_id)

## [v1.2.1] - 2025-03-15

### Fixed

- fix(title_handler): 修复 Comp.Plain 导入错误
- fix(title_handler): 正确导入 Plain 类替代 Comp.Plain

## [v1.2.0] - 2025-03-15

### Added

- feat(title_handler): 机器人反馈引用消息并 @ 群友
- feat(title_handler): 转发消息的额外头衔消息引用详细消息
- feat(database): 添加 clear_rate_limit 方法清空申请限制
- feat(main): 添加清空限制指令（超级管理员专用）
- feat(help_handler): 添加清空限制指令说明

### Changed

- refactor(title_handler): 使用 Reply + At + Plain 组件构建响应消息
- refactor(title_handler): 转发时获取 message_id 用于引用

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
