# 进度日志

## 会话：2026-07-29

### M1 验收加固（用户批准）
- **状态：** in_progress
- **开始时间：** 2026-07-29
- 范围限制：不扩展 Mooncell、MCP、社区掉落率或云部署。
- 已执行：
  - 复现并确认 Vite 只监听 IPv6 `::1`，而 `127.0.0.1:5173` 未监听。
  - 审计 `.gitignore`；`.env`、数据库、缓存与构建物已忽略。
  - 补充 `.env.*`、日志、PID 与通用缓存忽略规则。
  - 将 G0–G5 验收要求固化到 `task_plan.md`。
- 错误：
  - 沙箱用户无法写入由管理员所有的 `.git/config` 与 `.git/index`；基线提交需使用已授权的仓库写入权限。

### M0：工程基线与 Harness 骨架
- **状态：** complete
- **开始时间：** 2026-07-29
- 执行的操作：
  - 阅读项目规划文档并逐页验证。
  - 验证 Atlas CN 版本、静态导出与目标查询端点。
  - 验证社区掉落率仓库、文件结构、版本字段与许可缺口。
  - 读取项目规划、前端设计与 UI/UX 技能。
  - 建立持久化计划、发现与进度文件。
  - 完成 M0–M6 可运行纵切面、PostgreSQL 迁移、演示 UI 与文档。
- 创建/修改的文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`

## 测试结果
| 测试 | 输入 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| Atlas CN 版本 | `/info`, `/raw/CN/info` | 返回 CN 版本 | 返回 hash/serverHash/dataVer | 通过 |
| Atlas 中文查询 | 角色名、collectionNo、材料名 | 返回中文实体 | 返回预期 JSON | 通过 |
| 社区掉落率结构 | `dropData.json` | 可解析版本、样本与矩阵 | 96 物品、402 关卡 | 通过 |
| 后端测试 | 离线 Suite | 全部通过 | 21 通过、1 个在线测试默认跳过 | 通过 |
| Atlas 在线契约 | 版本、中文角色、中文材料 | 当前端点可用 | 1 通过 | 通过 |
| 后端静态检查 | `src`、`tests` | 无错误 | All checks passed | 通过 |
| 前端单元测试 | App 壳与禁用状态 | 通过 | 1 通过 | 通过 |
| 前端生产构建 | TypeScript + Vite | 成功 | 1629 modules transformed | 通过 |
| 前端 E2E | Edge 桌面/移动视口 | 成功 | 1 通过 | 通过 |
| PostgreSQL 迁移 | Alembic 0001–0002 | 建表成功 | 20 张 public 表 | 通过 |
| API 冒烟 | 搜索、缺口、计划、Trace、Replay | 返回可验证结果 | complete、21 事件、9 Checkpoint | 通过 |
| 离线评测 | gap-v1 | 50 条通过 | pass_rate=1.0 | 通过 |

## 错误日志
| 时间戳 | 错误 | 尝试次数 | 解决方案 |
|--------|------|---------|---------|
| 2026-07-29 | Atlas HEAD 请求连接中断 | 1 | 改用单字节 Range 请求 |
| 2026-07-29 | raw.githubusercontent.com 证书吊销检查失败 | 1 | 改用 GitHub API Base64 内容 |
| 2026-07-29 | uv 缓存目录拒绝访问 | 1 | 使用工作区 `.uv-cache` |
| 2026-07-29 | Vitest 收集到 Playwright 文件 | 1 | 限定测试文件范围 |
| 2026-07-29 | Playwright 缺少 Chromium | 1 | 复用系统 Edge |
| 2026-07-29 | PostgreSQL 缺少 vector 扩展 | 1 | pgvector 改为可选迁移，JSON 向量后备 |
| 2026-07-29 | dropData 根节点解析为 0 行 | 1 | 解包 `domusAurea` 后再解析矩阵 |
| 2026-07-29 | PostgreSQL 验证命令等待密码超时 | 1 | 显式设置 PGPASSWORD 后确认迁移已完成 |

## 五问重启检查
| 问题 | 答案 |
|------|------|
| 我在哪里？ | 核心实现与最终验证已完成 |
| 我要去哪里？ | 外部 Mooncell 生产语料许可复核与用户指定的公开部署 |
| 目标是什么？ | 交付可运行、可测试、可演示的 QuestPilot |
| 我学到了什么？ | 见 `findings.md` |
| 我做了什么？ | 完成全栈实现、测试、PostgreSQL 迁移、数据边界与演示材料 |

---
*每个阶段完成后或遇到错误时更新此文件*
