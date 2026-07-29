# QuestPilot 实施计划

## 目标
交付一个可运行、可测试、可演示的复杂养成游戏规划 Agent：M1 完成确定性材料闭环，M3 完成受约束的局部资源规划，M5 完成 Replay、评测与可观测性，M6 提供 MCP 与通用适配示例。

## 当前阶段
真实社区掉落率与受约束规划：approved / P0 in_progress。连续执行 P0–P6；仅在数据无法验证、密钥安全风险或核心架构无法继续时提前暂停。

## 当前批准范围：可运行性与 M1 验收加固

### G0：安全基线与版本锚点
- [x] 审计 `.gitignore` 对 `.env`、密钥、数据库、缓存、日志的覆盖
- [x] 创建基线提交并打 `m1-generated-baseline` 标签
- [x] 确认仓库候选文件中不存在真实 API 密钥
- **状态：** complete

### G1：固定地址与简单启动工具
- [x] 前端固定 `127.0.0.1:5173` 并启用 `strictPort`
- [x] 后端固定 `127.0.0.1:8000`
- [x] CORS 同时允许 `localhost:5173` 与 `127.0.0.1:5173`
- [x] README 只推荐 `http://127.0.0.1:5173/`
- [x] 完成 `doctor.ps1`、`start.ps1`、`stop.ps1`
- [x] `start.ps1` 验证前后端健康并打印可点击地址
- **状态：** complete

### G2：真实 Atlas CN 与单技能验收
- [x] 导入真实 Atlas CN 角色、技能和材料，保存版本、来源与更新时间
- [x] 页面显示 Atlas 版本、来源和更新时间
- [x] 随机选取至少 3 名角色，与公开资料人工核对技能材料
- [x] 单角色、单技能库存与缺口闭环通过
- **状态：** complete

### G3：多目标与轻量纠错
- [x] 支持多个角色/技能目标的添加和删除
- [x] 合并重复目标并确定性汇总材料缺口
- [x] 搜索顺序为精确名称/别名优先，再返回模糊候选
- [x] 低置信度不静默纠正，多候选时要求用户选择
- **状态：** complete

### G4：DeepSeek V4 Flash 与分层验收
- [x] DeepSeek 配置仅从 `.env` 读取，前端、日志、Git、Fixture 不含密钥
- [x] 使用 `https://api.deepseek.com`、`deepseek-v4-flash`，显式关闭 thinking
- [x] 分别报告确定性测试、FakeModel 轨迹测试、DeepSeek 在线测试
- [x] 增加 10–20 条真实自然语言冒烟任务
- [x] 验证意图解析、别名、工具选择、参数与最终解释
- [x] 将 gap-v1 重命名为“材料缺口单元评测”，不表述为完整 Agent 评测
- **状态：** complete

### G5：阶段暂停与评审
- [x] 启动验收通过
- [x] 真实 Atlas 数据验收通过
- [x] 多目标缺口验收通过
- [x] DeepSeek 冒烟验收通过
- [x] 向用户报告实际结果并暂停，等待是否进入社区掉落率与复杂规划
- **状态：** complete / paused_for_review

## 当前批准阶段：真实社区掉落率与受约束规划

目标：在不宣称全服全量最优、不公开再分发许可未确认原始数据的前提下，用真实且固定版本的社区观测数据完成小规模可解释规划闭环。

### P0：M1 交付封板（0.5 天）
- [x] 用户人工验收标准名称、别名、同名歧义、错别字候选与多目标功能
- [x] 重复目标改为“后一次完整覆盖前一次”，前后端和 E2E 明确验证
- [x] 输入严格满足 `1 ≤ 当前等级 ≤ 目标等级 ≤ 10`
- [x] 再次执行密钥扫描、确定性测试、FakeModel、前端与启动验收
- [x] 提交前向用户列出最终 diff 摘要
- [x] 创建 M1 验收提交并打 `m1-accepted` 标签
- **门禁：** P0 测试或密钥扫描失败时，不进入社区数据下载与发布
- **状态：** complete

### P1：来源、许可与版本清单（0.5–1 天）
- [ ] 复核 `chaldea-data` 当前提交、许可证声明、文件来源与上游归属
- [ ] 为 `dropData.json` 建立固定提交、`domusVer`、SHA-256、抓取时间与许可状态清单
- [ ] 原始文件仅进入 gitignored 本地缓存；公开仓库只保留 Adapter、清单和合成 Fixture
- [ ] 许可不明确时，UI 和文档明确标记“本地验证数据，不随项目再分发”
- **门禁：** 来源、哈希或许可状态缺失时禁止 publish
- **状态：** approved / pending

### P2：小规模真实数据集发布（1–2 天）
- [ ] 从 Atlas CN 建立关卡 ID、名称、章节、AP 与永久性事实
- [ ] 从社区数据读取掉落率、样本数和数据集版本，不混入 Atlas Adapter
- [ ] 只选择与 M1 演示目标有交集的 3–5 种材料、10–20 个永久自由关卡
- [ ] 排除活动、随机敌人、缺少样本数、无法映射 Atlas 关卡 ID 的记录
- [ ] 实现 `fetch → cache → adapt → validate → stage → publish` 与整批回滚
- [ ] 页面/API 展示数据版本、样本量、候选范围、抓取时间与许可状态
- [ ] 缓存经许可的角色与材料图片；下载失败使用本地占位图且不影响核心流程
- [ ] 图片清单记录来源与本地缓存状态，不长期热链第三方服务器
- **门禁：** 损坏、空覆盖、低样本或 Atlas 映射失败的数据集不得发布
- **状态：** approved / pending

### P3A：确定性规划基线（1 天）
- [ ] 明确目标函数：固定候选集内最小期望 AP，次级目标为较少运行次数
- [ ] 输入约束：材料缺口、当前 AP、苹果、每日时间、截止日期与单次耗时
- [ ] 先实现简单、确定性、可端到端验证的基线规划器
- [ ] 未覆盖材料返回“无已验证路线”，不得补猜掉落率

### P3B：有界 branch-and-bound（1–2 天）
- [ ] 在基线可运行的前提下实现 branch-and-bound，并设置节点数和时间上限
- [ ] 用穷举 Oracle 验证小型合成问题的局部最优性
- [ ] 达到搜索上限时返回可验证的 best-so-far 与明确降级说明
- [ ] 同一种求解实现连续失败两次后停止重写，保留基线规划器并记录原因
- **边界：** 只对固定候选集声明局部最优，不做全服全量或活动全局最优
- **状态：** approved / pending

### P4：LangGraph 与 Harness 接入（1–2 天）
- [ ] 使用既有流程：`calculate_gap → load_dataset → search_candidates → generate → validate`
- [ ] Checkpoint 保存目标、库存、Atlas 版本、掉落数据版本与规划器版本
- [ ] 执行预算、超时、幂等重试、循环检测与恢复
- [ ] 确定性验证材料覆盖、库存、AP、日期、候选范围和数据版本
- [ ] Trace 记录节点、工具参数摘要、候选淘汰原因、规划耗时与降级原因
- **约束：** 模型只解析目标与解释结果，不参与数值优化或掉落率猜测
- **状态：** approved / pending

### P5：前端计划闭环（1–2 天）
- [ ] 复用 M1 多目标清单，增加 AP、苹果、截止日期和每日时间输入
- [ ] 增加自然语言入口，通过 DeepSeek V4 Flash 解析一个或多个角色/技能/当前等级/目标等级
- [ ] 同名与低置信度候选要求用户选择；解析目标按“后一次完整覆盖”加入清单
- [ ] 材料缺口与路线数值仍只由确定性工具计算，模型不得估算掉率或做数值优化
- [ ] 展示简化模型解析结果、工具调用步骤与最终确定性计划
- [ ] 展示关卡、次数、期望掉落、样本数、预计 AP 与资源是否足够
- [ ] 固定展示版本、候选范围、“局部最优”与社区观测不确定性
- [ ] 展示无覆盖、预算不足、截止日期不可达和搜索降级状态
- [ ] 从计划结果进入 Trace，查看数据与验证证据
- [ ] 搜索、目标、材料缺口、解析结果和路线尽量图文结合；所有图片提供 alt 与文字后备
- **状态：** approved / pending

### P6：分层验收与暂停（1–2 天）
- [ ] Adapter/版本/索引/过滤/回滚单元测试
- [ ] 规划器穷举 Oracle、确定性、预算、日期、无覆盖与降级测试
- [ ] FakeModel 规划轨迹与 Checkpoint 恢复测试
- [ ] 8–12 条真实自然语言规划冒烟任务
- [ ] 浏览器 E2E：自然语言/手工多目标 → 后输入覆盖 → 缺口 → 资源边界 → 局部路线 → Trace
- [ ] 输出真实测试报告并暂停，等待是否进入 Mooncell 生产 RAG 或作品集收尾
- **状态：** approved / pending

### 本阶段明确不做
- 全量掉落率公开再分发、全服全局最优、活动动态规划
- Mooncell 生产语料扩展、MCP 扩展、云部署
- 截图识别、伤害模拟、队伍推荐、多 Agent

预计投入：8–12 个兼职开发日。P2、P3、P6 是主要风险点；正常功能阶段连续执行，不设置中途审批暂停。

## 各阶段

### M0：工程基线与 Harness 骨架
- [x] 建立后端、前端、测试、文档、脚本和 CI
- [x] 实现 ModelGateway、FakeModel、ToolSpec、ToolRegistry
- [x] 实现 ExecutionContext、ExecutionEvent 与事件接收器
- [x] 建立数据库、配置、迁移和健康检查
- [x] 通过无网络 Harness 单元测试
- **状态：** complete

### M1：确定性 MVP 与受控 Tool Calling
- [x] 实现角色、材料、技能消耗、库存与目标模型
- [x] 实现 Atlas CN 索引、材料与按角色详情导入
- [x] 实现角色查询、库存、材料缺口 API
- [x] 所有 Agent Tool Calling 经过 Gateway 与 Registry
- [x] 实现角色搜索、库存与目标结果前端
- **状态：** complete

### M2：结构化数据管线
- [x] 实现 fetch/snapshot/adapt/validate/stage/publish
- [x] 实现版本、哈希、ETag、幂等与快照降级
- [x] 实现冲突记录和 Docker Compose
- **状态：** complete

### M3：LangGraph、运行策略与局部规划
- [x] 实现 ContextBuilder、Checkpoint、Policy、Trace
- [x] 实现预算、幂等重试、超时与循环检测
- [x] 实现社区掉落率适配器与小规模版本数据集
- [x] 实现局部规划、确定性验证、降级和 SSE
- **状态：** complete

### M4：Mooncell RAG
- [x] 实现抓取、清洗、切分、PostgreSQL 全文与向量检索后备
- [x] 实现来源元数据、重排、引用与离线快照降级
- [ ] 填充并许可复核 20–30 个生产页面（当前仅提交合成演示内容）
- **状态：** implementation_complete / corpus_pending

### M5：完整 Harness、评测与可观测性
- [x] 实现 Replay、多模型降级、Prompt Registry
- [x] 实现 OpenTelemetry 接入与 Trace 查询
- [x] 实现 50 条离线评测、回归报告和 Trace/Replay 前端
- **状态：** complete

### M6：MCP、通用化与部署
- [x] 用同一 ToolRegistry 暴露 MCP 工具
- [x] 实现 Mock RPG Adapter
- [x] 完善 Compose、可选鉴权/缓存/对象存储接口、演示、README 与架构说明
- [ ] 执行公开云部署（缺少用户指定的部署目标与凭据）
- **状态：** implementation_complete / deployment_pending

### 最终验证
- [x] 后端测试、静态检查和导入检查通过
- [x] 前端测试、E2E 与生产构建通过
- [x] PostgreSQL 迁移与关键 API 冒烟测试通过
- [x] 数据许可边界和运行说明清晰
- **状态：** complete

## 已做决策
| 决策 | 理由 |
|------|------|
| 单体仓库、前后端分离 | 保持作品集可理解性，避免过早微服务化 |
| PostgreSQL 为主，测试允许 SQLite | 兼顾目标架构与隔离测试 |
| Harness 从 M0 渐进建设 | 避免 M5 大规模重构 |
| Atlas CN 为结构化事实主源 | 已验证中文端点、静态导出与版本接口 |
| 掉落率独立于 Atlas | 它是社区观测数据，具有版本和样本不确定性 |
| M3 只做固定候选集局部规划 | 不以全量数据和全局最优阻塞核心演示 |
| 社区原始掉落率不提交 | chaldea-data 未声明仓库许可证 |
| UI 采用“迦勒底作战台”视觉方向 | 贴合规划、状态追踪和游戏数据主题 |

## 遇到的错误
| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| uv 默认缓存目录无写权限 | 1 | 将缓存切换到项目内 `.uv-cache` |
| 沙箱禁止 Python/Node 首次联网下载 | 1 | 经授权完成基础依赖下载 |
| Vitest 误收集 Playwright 用例 | 1 | 限定 Vitest include 范围 |
| Vite 配置缺少 Vitest 类型 | 1 | 从 `vitest/config` 导入 defineConfig |
| Playwright Chromium 下载卡住 | 1 | 改用本机 Edge，E2E 通过 |
| Windows PostgreSQL 未安装 pgvector | 1 | 核心迁移改用 JSON 后备，pgvector 变为显式可选迁移 |
| 真实 dropData 顶层结构不同 | 1 | 适配 `domusAurea` 包装并加入真实形状 Fixture |
| `.git` 目录归管理员所有，沙箱用户无法创建 index.lock | 1 | 使用受控提升权限完成用户明确要求的基线提交与标签 |
| PowerShell 5.1 误解码无 BOM UTF-8 中文脚本 | 1 | 启动脚本使用 ASCII 输出，避免依赖 BOM 和系统代码页 |
| `Start-Process` 合并 Path/PATH 时键冲突 | 2 | 放弃 `Start-Process`，改用 .NET `ProcessStartInfo` |
| 长期子进程继承调用命令输出句柄，外层一直显示 Running | 2 | 使用 `UseShellExecute=true` 脱离输出句柄，并分离启动与健康检查 |
| DeepSeek 冒烟 JSON 根数组被 PowerShell 5.1 包成单项 | 1 | 显式遍历展开并在联网前校验任务数为 10–20 |

## 完成标准
- 不是仅有接口和空目录；每个里程碑必须具备可运行实现与测试。
- 外部服务无密钥或不可访问时，FakeModel、固定 Fixture 和最后快照仍可完成核心测试。
- 所有精确数字由确定性代码计算，模型只做意图与工具编排。
