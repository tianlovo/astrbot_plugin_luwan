# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [v1.3.8] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复 AiocqhttpPlatformAdapter 导入路径错误
- fix(image_forwarder): 模块名应为 aiocqhttp_platform_adapter
- fix(image_forwarder): 类名应为 AiocqhttpPlatformAdapter

## [v1.3.7] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复 PlatformAdapterType 导入路径错误
- fix(image_forwarder): 从 astrbot.core.star.filter.platform_adapter_type 导入

## [v1.3.6] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复 UMO 格式不正确问题
- fix(image_forwarder): 使用 platform.metadata.id 获取正确的平台 ID
- fix(image_forwarder): 使用 self.context.send_message() 发送主动消息
- fix(image_forwarder): 正确构建 unified_msg_origin 格式

## [v1.3.5] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复找不到平台适配器问题
- fix(image_forwarder): 使用 self.context.get_platform() 获取平台适配器
- fix(image_forwarder): 使用 platform.send_group_message() 发送群消息
- fix(image_forwarder): 移除手动构建 UMO 的代码

## [v1.3.4] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复 MessageChain 使用错误
- fix(image_forwarder): 使用 chain.file_image() 替代 chain.append()

## [v1.3.3] - 2025-03-15

### Changed

- refactor(image_forwarder): 仅处理本地路径图片
- refactor(image_forwarder): 网络 URL 图片跳过并记录警告日志
- refactor(image_forwarder): 使用 Comp.Image.fromFileSystem() 发送本地图片

## [v1.3.2] - 2025-03-15

### Changed

- refactor(image_forwarder): 使用 MessageChain 构建消息
- refactor(image_forwarder): 使用 self.context.send_message() 发送主动消息
- refactor(image_forwarder): 仅发送图片，移除文字描述

## [v1.3.1] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复 Image.fromBytes() 参数错误
- fix(image_forwarder): 移除多余的 MIME 类型参数

## [v1.3.0] - 2025-03-15

### Added

- feat(comupik): 添加 ComuPik 图片转发功能
- feat(comupik_client): 实现 ComuPik API 客户端，支持轮询获取图片
- feat(image_forwarder): 实现图片转发服务，定时轮询并转发到 QQ 群
- feat(config): 添加 ComuPik 配置项（enabled, api_url, target_groups, poll_interval, poll_time_range）
- feat(database): 添加 comupik_forwarded_images 表记录已转发图片
- feat(main): 集成图片转发功能到主插件

### Features

- 支持从 ComuPik 插件获取 Telegram 图片
- 支持将图片转发到配置的 QQ 群列表
- 支持启用/禁用开关（默认启用）
- 支持配置轮询间隔（默认30秒）
- 支持配置轮询时间范围（默认12小时）
- 自动记录已转发图片，避免重复转发
- 优化 exclude_ids 查询，只获取时间范围内的记录

## [v1.2.10] - 2025-03-15

### Fixed

- fix(title_handler): 恢复使用 `await event.send()` 发送消息
- fix(title_handler): 恢复消息引用功能（取消注释 Comp.Reply）
- fix(title_handler): 添加 `-> None` 返回类型注解
- fix(main): 使用 `await` 直接调用处理方法

## [v1.2.9] - 2025-03-15

### Fixed

- fix(main): 修复生成器调用方式
- fix(main): 将 `await` 改回 `async for _ in ...` 正确迭代生成器

## [v1.2.8] - 2025-03-15

### Fixed

- fix(main): 将 `yield` 改回 `await`，恢复普通方法调用
- fix(title_handler): 暂时禁用消息引用功能（注释掉 Comp.Reply）
- fix(title_handler): 保留 @ 用户功能

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
