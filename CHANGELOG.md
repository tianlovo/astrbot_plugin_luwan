# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

## [v1.7.11] - 2025-03-20

### Added

- feat(mute): 禁言冷却中时发送通知提示剩余时间

## [v1.7.10] - 2025-03-20

### Fixed

- fix(mute): 确保投票群组隔离，一个群同时只能有一个投票

## [v1.7.9] - 2025-03-20

### Changed

- feat(mute): 允许发起人和目标用户参与投票

## [v1.7.8] - 2025-03-20

### Fixed

- fix(mute): 将handle_vote_response_raw中的DEBUG日志改为INFO级别

## [v1.7.7] - 2025-03-20

### Fixed

- fix(mute): 将DEBUG日志改为INFO级别以便排查问题
- fix(mute): 添加更详细的条件判断日志

## [v1.7.6] - 2025-03-20

### Fixed

- fix(mute): 修复投票收集失败问题，支持处理@机器人的消息格式
- fix(mute): 添加详细调试日志以便排查问题
- fix(mute): 改进消息文本清理逻辑，兼容多种@格式

## [v1.7.5] - 2025-03-20

### Fixed

- fix(mute): 修复at获取逻辑，跳过机器人at获取目标用户
- fix(mute): 投票通知不at且显示群昵称
- fix(mute): 投票通知at目标用户并发送投票结果
- fix(mute): 投票结果通知引用投票消息
- fix(mute): 改用消息监听方式统计投票而非命令注册
- fix(mute): 改用on_group_message方式收集投票消息

### Added

- feat(mute): 添加禁言投票子命令（禁言 @用户 / 好 / 不好）
- feat(mute): 投票通知显示发起人和投票时长

## [v1.7.4] - 2025-03-19

### Fixed

- fix(mute): 防止同一用户重复投票

### Added

- feat(mute): 添加禁言投票子命令（禁言 @用户 / 好 / 不好）

## [v1.7.3] - 2025-03-19

### Added

- feat(mute): 添加"禁言我"命令
- feat(mute): 支持配置启用开关和群组列表

### Refactored

- refactor(mute): 将禁言我处理器移至command包
- refactor(config): 将禁言我配置归入mute父级

## [v1.7.2] - 2025-03-19

### Fixed

- fix(poke): 防止机器人戳自己
- fix(poke): 反戳和跟戳时机器人也不能戳自己

## [v1.7.1] - 2025-03-19

### Added

- feat(poke): 添加反戳功能（被戳时戳回去）
- feat(poke): 添加跟戳功能（其他人被戳时随机跟戳）

## [v1.7.0] - 2025-03-19

### Fixed

- fix(poke): 使用 event.bot.group_poke 发送戳一戳

## [v1.6.8] - 2025-03-19

### Added

- feat(poke): 添加戳一戳服务，基于概率模型决定是否戳一戳发言人
- feat(poke): 支持配置启用群列表、触发词、权重参数、冷却时间

## [v1.6.7] - 2025-03-19

### Fixed

- fix(test): 修复消息分析功能的多个问题

## [v1.6.6] - 2025-03-19

### Added

- feat(test): 添加"测试 分析"子命令，可切换开启/关闭指定群的消息分析功能
- feat(test): 对开启分析功能的群，每条消息都会被解析并转发，特别是 JSON 消息

## [v1.6.5] - 2025-03-19

### Changed

- refactor(test): 通过 bot API 调用 get_mini_app_ark 获取小程序卡片 JSON

## [v1.6.4] - 2025-03-19

### Changed

- refactor(test): 使用 Comp.Json 发送 app_mini_program 格式的 Bilibili 小程序卡片

## [v1.6.3] - 2025-03-19

### Fixed

- fix(test): 修复测试分享消息 chain 构建方式

## [v1.6.2] - 2025-03-19

### Added

- feat(test): 添加"测试"命令，仅超级管理员可用
- feat(test): 添加"测试 分享"子命令，使用 Comp.Share 发送分享卡片

## [v1.6.1] - 2025-03-19

### Fixed

- fix(messages): 将 Messages.get() 改为 @classmethod 解决单例模式下调用问题

## [v1.6.0] - 2025-03-19

### Changed

- refactor(infra): 将 config.py, database.py, messages.py 移动到 infra/ 包下
- refactor(infra): 重命名为 infra_config.py, infra_database.py, infra_messages.py
- refactor(infra): 更新所有导入语句适配新的文件路径

## [v1.5.9] - 2025-03-19

### Changed

- refactor(messages): 实现消息字符串外部化系统
- refactor(messages): 新增 `messages.json` 存储所有可配置文本
- refactor(messages): 新增 `messages.py` 提供统一的消息获取接口
- refactor(messages): 更新 main.py, command/*.py 使用消息系统
- refactor(messages): 保留内部日志字符串，仅外部化用户可见文本

## [v1.5.8] - 2025-03-19

### Changed

- refactor(project): 重构项目结构，提高代码可维护性
- refactor(service): 将后台服务类移至 `service/` 包，添加 `srv_` 前缀
  - `group_checkin.py` -> `service/srv_group_checkin.py`
  - `image_forwarder.py` -> `service/srv_image_forwarder.py`
  - `comupik_client.py` -> `service/srv_comupik_client.py`
- refactor(command): 将指令处理类移至 `command/` 包，添加 `cmd_` 前缀和 `_handler` 后缀
  - `title_handler.py` -> `command/cmd_title_handler.py`
  - `help_handler.py` -> `command/cmd_help_handler.py`
- refactor(main): 更新所有导入语句，适配新的文件路径

## [v1.5.7] - 2025-03-19

### Added

- feat(checkin): 添加"打卡"命令，支持在群聊中手动触发机器人打卡
- feat(checkin): 添加"打卡 状态"命令，超级管理员可查看打卡配置和状态
- feat(checkin): 支持查看当前群是否在打卡列表、今日是否已打卡、计划打卡时间
- feat(checkin): 状态命令显示时区、打卡时段、打卡欲望、保底功能等配置信息

## [v1.5.6] - 2025-03-19

### Added

- feat(group_checkin): 添加时区配置支持
- feat(group_checkin): 支持配置时区如 Asia/Shanghai、Asia/Tokyo、America/New_York 等
- feat(group_checkin): 所有打卡时间按配置时区计算并转换为本地时间执行
- feat(group_checkin): 日志显示配置时区和本地时间的对比

### Fixed

- fix(config): 移除 _conf_schema.json 中的尾随逗号，确保符合 JSON 标准

## [v1.5.5] - 2025-03-19

### Changed

- feat(group_checkin): 每小时输出日志显示每个群的下一次打卡时间
- feat(group_checkin): 添加 `_log_next_checkin_times` 方法输出打卡计划
- feat(group_checkin): 日志显示群打卡状态（已完成/已失败/计划时间）
- feat(group_checkin): 日志显示保底检查时间

## [v1.5.4] - 2025-03-19

### Changed

- feat(group_checkin): 确保每个群每天的随机打卡时间点都不重复
- feat(group_checkin): 添加 `_used_times` 字典记录每个群已使用过的打卡时间
- feat(group_checkin): 生成新时间时自动排除已使用的时间点
- feat(group_checkin): 当所有时间点都用完后清空历史重新开始

## [v1.5.3] - 2025-03-19

### Changed

- refactor(group_checkin): 重新设计打卡逻辑
- feat(group_checkin): 每个群每天在配置时间段内随机挑选一个时间点打卡一次
- feat(group_checkin): 打卡成功后当天不再打卡
- feat(group_checkin): 打卡失败可在时间段内重试3次
- feat(group_checkin): 3次失败后发送私聊消息通知超级管理员
- feat(group_checkin): 添加 `_generate_scheduled_times` 方法生成随机打卡时间
- feat(group_checkin): 添加 `_try_checkin` 方法实现重试机制
- feat(group_checkin): 添加 `_reschedule_checkin_time` 方法重新安排打卡时间
- feat(group_checkin): 添加 `_notify_admin` 方法通知管理员

## [v1.5.2] - 2025-03-19

### Changed

- fix(group_checkin): 修改打卡保底逻辑
- fix(group_checkin): 当整个群一整天（从00:00到保底检查时间）都没有任何人（包括机器人和群成员）打卡时，才触发保底打卡
- feat(group_checkin): 添加 `_check_group_has_any_checkin_today` 方法，通过API查询群打卡记录

## [v1.5.1] - 2025-03-19

### Changed

- refactor(group_checkin): 将群打卡配置从每个群独立配置改为全局配置
- refactor(config): `group_checkin.groups` 改为 `group_checkin.target_groups`（仅群号列表）
- refactor(config): `start_time`、`end_time`、`desire` 改为全局配置，所有群统一使用

### Configuration

群打卡配置项（v1.5.1）：
- `group_checkin.enabled`: 是否启用群打卡
- `group_checkin.target_groups`: 打卡群号列表
- `group_checkin.start_time`: 打卡开始时间（HH:MM）
- `group_checkin.end_time`: 打卡结束时间（HH:MM）
- `group_checkin.desire`: 打卡欲望（0-100%）
- `group_checkin.check_interval`: 检查间隔（分钟）
- `group_checkin.enable_guarantee`: 是否启用打卡保底
- `group_checkin.guarantee_check_time`: 保底检查时间（HH:MM）
- `group_checkin.guarantee_start_time`: 保底统计开始时间（HH:MM）

## [v1.5.0] - 2025-03-19

### Added

- feat(group_checkin): 新增群打卡功能
- feat(group_checkin): 支持配置多个QQ群自动打卡
- feat(group_checkin): 每个群可独立配置打卡时间段（HH:MM格式）
- feat(group_checkin): 每个群可独立配置打卡欲望（0-100%概率）
- feat(group_checkin): 支持配置多条打卡消息随机选择
- feat(group_checkin): 每日自动重置，避免重复打卡
- feat(config): 添加群打卡配置项到 WebUI
- feat(database): 添加群打卡记录表

## [v1.4.0] - 2025-03-19

### Removed

- **BREAKING**: 移除QQ聊天交互式配置功能
- 移除 `鹿丸配置` / `lw配置` 指令
- 移除 `清空限制` / `重置限制` / `清除限制` 指令
- 配置管理统一使用 AstrBot WebUI

### Migration

- 管理员请通过 AstrBot 管理面板进行配置
- WebUI 路径：插件配置 → 鹿丸插件

## [v1.3.9] - 2025-03-15

### Fixed

- fix(image_forwarder): 修复类名错误
- fix(image_forwarder): 类名应为 AiocqhttpAdapter 而非 AiocqhttpPlatformAdapter

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
