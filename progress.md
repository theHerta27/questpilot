# 进度日志

## 会话：2026-07-29

### 真实社区掉落率与受约束规划
- **状态：** approved / P0 sealing
- **批准时间：** 2026-07-29
- 用户要求连续执行 P0–P6，不设置自然语言入口中途暂停；仅在数据验证、密钥安全或核心架构阻塞时提前暂停。
- P0 先将重复目标调整为“后一次完整覆盖前一次”，完成密钥扫描与分层测试后提交并标记 `m1-accepted`。
- P3 拆分为可运行的确定性基线与有界 branch-and-bound；同一求解实现连续失败两次即保留基线并报告。
- P5 并入 DeepSeek 自然语言多目标入口和经许可的本地图片缓存；P6 统一完成在线冒烟与浏览器 E2E。
- P0 实测：后端 34 通过/1 在线契约跳过，Ruff 通过，前端 Vitest 6/6，构建通过，Playwright 2/2，FakeModel/Harness 5/5，材料缺口单元评测 50/50，DeepSeek 在线 12/12。
- 密钥扫描未发现 `sk-` 形式秘密；`.env` 已由 `.gitignore` 明确排除，唯一受控环境文件为无密钥的 `.env.example`。
- 仅新增“真实社区掉落率与受约束规划”P0–P6 评审计划。
- 未下载社区原始数据，未修改规划器，未扩展 Mooncell、MCP 或云部署。
- 核心门禁：先封板 M1，再核验来源/许可/哈希；只发布 3–5 种材料、10–20 个永久关卡的小规模版本数据集。
- 规划器建议使用有上限的确定性 branch-and-bound，并以小型穷举 Oracle 验证局部最优性。
- 预计 8–12 个兼职开发日，P2、P3、P6 分别作为数据、算法与验收暂停点。

### M1 验收加固（用户批准）
- **状态：** complete / paused_for_review
- **开始时间：** 2026-07-29
- **完成时间：** 2026-07-29
- 范围限制：不扩展 Mooncell、MCP、社区掉落率或云部署。
- 已执行：
  - 复现并确认 Vite 只监听 IPv6 `::1`，而 `127.0.0.1:5173` 未监听。
  - 审计 `.gitignore`；`.env`、数据库、缓存与构建物已忽略。
  - 补充 `.env.*`、日志、PID 与通用缓存忽略规则。
  - 将 G0–G5 验收要求固化到 `task_plan.md`。
  - 创建基线提交 `22cf03c` 并打 `m1-generated-baseline` 标签。
  - 提交候选密钥模式扫描未发现真实 API 密钥。
  - 固定前端 `127.0.0.1:5173`、`strictPort`、后端 `127.0.0.1:8000` 与双来源 CORS。
  - 完成 `doctor.ps1`、`start.ps1`、`stop.ps1`，干净启动约 6–7 秒并通过双端健康检查。
  - 同步 Atlas CN `ec2a23` / `dataVer 966`：1,870 条材料与真实角色快照。
  - 固定种子抽取伊阿宋、Archer 刑部姬、雅克·德·莫莱并逐级核对公开技能材料。
  - 修复 Atlas 当前共享 `skillMaterials` 结构适配，映射到三个主动技能。
  - 完成精确名称/别名优先、模糊候选、同名选择与确定性 Agent 护栏。
  - 完成前端多角色/多技能目标添加、删除、重复目标合并和来源版本展示。
  - 接入 DeepSeek V4 Flash，显式关闭 thinking，正式 12 条自然语言冒烟全部通过。
  - 将 50 条减法套件重命名为“材料缺口单元评测”。
  - 完成 `docs/m1-acceptance-report.md` 并按用户要求暂停。
- 错误：
  - 沙箱用户无法写入由管理员所有的 `.git/config` 与 `.git/index`；基线提交需使用已授权的仓库写入权限。
  - Windows PowerShell 5.1 将无 BOM UTF-8 中文脚本误解码并产生语法错误；脚本运行输出改为 ASCII，README 保留中文。
  - 当前终端同时含 `Path`/`PATH` 环境键，PowerShell 5.1 `Start-Process` 合并时冲突；`-UseNewEnvironment` 仍失败，改用已验证的 .NET `ProcessStartInfo`。
  - 长期子进程继承命令输出句柄导致外层一直显示 Running；改为 Shell 脱离进程并分离健康检查。
  - PowerShell 5.1 首次将冒烟 JSON 根数组包装成单项；显式展开并增加 10–20 条前置计数检查。

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
| 后端测试 | 离线 Suite | 全部通过 | 31 通过、1 个在线测试默认跳过 | 通过 |
| Atlas 在线契约 | 版本、中文角色、中文材料 | 当前端点可用 | 1 通过 | 通过 |
| 后端静态检查 | `src`、`tests` | 无错误 | All checks passed | 通过 |
| 前端单元测试 | App 壳与禁用状态 | 通过 | 1 通过 | 通过 |
| 前端生产构建 | TypeScript + Vite | 成功 | 1629 modules transformed | 通过 |
| 前端 E2E | Edge 桌面/移动视口 | 成功 | 1 通过 | 通过 |
| PostgreSQL 迁移 | Alembic 0001–0002 | 建表成功 | 20 张 public 表 | 通过 |
| API 冒烟 | 搜索、缺口、计划、Trace、Replay | 返回可验证结果 | complete、21 事件、9 Checkpoint | 通过 |
| 材料缺口单元评测 | material-gap-unit-v1 | 50 条通过 | 50/50，pass_rate=1.0 | 通过 |
| FakeModel 轨迹 | Tool Call 与模糊候选护栏 | 同一 Harness 且不越权 | 2/2 | 通过 |
| DeepSeek 在线冒烟 | 12 条真实自然语言任务 | 工具、参数、别名与解释通过 | 12/12，154 事件 | 通过 |
| M1 启动验收 | doctor/start/health | 标准双端地址可访问 | Web 200、API ok | 通过 |

## 错误日志
| 时间戳 | 错误 | 尝试次数 | 解决方案 |
|--------|------|---------|---------|
| 2026-07-29 | PowerShell 将带嵌套 f-string 的 `python -c` 误解析为 ScriptBlock | 1 | 不再使用多层内联引号；改用既有 pytest/CLI 入口逐条执行 |
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
