# QuestPilot 实施计划

## 目标
交付一个可运行、可测试、可演示的复杂养成游戏规划 Agent：M1 完成确定性材料闭环，M3 完成受约束的局部资源规划，M5 完成 Replay、评测与可观测性，M6 提供 MCP 与通用适配示例。

## 当前阶段
M1 验收加固：in_progress。暂停 Mooncell、MCP、社区掉落率扩展与云部署。

## 当前批准范围：可运行性与 M1 验收加固

### G0：安全基线与版本锚点
- [x] 审计 `.gitignore` 对 `.env`、密钥、数据库、缓存、日志的覆盖
- [ ] 创建基线提交并打 `m1-generated-baseline` 标签
- [ ] 确认仓库候选文件中不存在真实 API 密钥
- **状态：** in_progress

### G1：固定地址与简单启动工具
- [ ] 前端固定 `127.0.0.1:5173` 并启用 `strictPort`
- [ ] 后端固定 `127.0.0.1:8000`
- [ ] CORS 同时允许 `localhost:5173` 与 `127.0.0.1:5173`
- [ ] README 只推荐 `http://127.0.0.1:5173/`
- [ ] 完成 `doctor.ps1`、`start.ps1`、`stop.ps1`
- [ ] `start.ps1` 验证前后端健康并打印可点击地址
- **状态：** pending

### G2：真实 Atlas CN 与单技能验收
- [ ] 导入真实 Atlas CN 角色、技能和材料，保存版本、来源与更新时间
- [ ] 页面显示 Atlas 版本、来源和更新时间
- [ ] 随机选取至少 3 名角色，与公开资料人工核对技能材料
- [ ] 单角色、单技能库存与缺口闭环通过
- **状态：** pending

### G3：多目标与轻量纠错
- [ ] 支持多个角色/技能目标的添加和删除
- [ ] 合并重复目标并确定性汇总材料缺口
- [ ] 搜索顺序为精确名称/别名优先，再返回模糊候选
- [ ] 低置信度不静默纠正，多候选时要求用户选择
- **状态：** pending

### G4：DeepSeek V4 Flash 与分层验收
- [ ] DeepSeek 配置仅从 `.env` 读取，前端、日志、Git、Fixture 不含密钥
- [ ] 使用 `https://api.deepseek.com`、`deepseek-v4-flash`，显式关闭 thinking
- [ ] 分别报告确定性测试、FakeModel 轨迹测试、DeepSeek 在线测试
- [ ] 增加 10–20 条真实自然语言冒烟任务
- [ ] 验证意图解析、别名、工具选择、参数与最终解释
- [ ] 将 gap-v1 重命名为“材料缺口单元评测”，不表述为完整 Agent 评测
- **状态：** pending

### G5：阶段暂停与评审
- [ ] 启动验收通过
- [ ] 真实 Atlas 数据验收通过
- [ ] 多目标缺口验收通过
- [ ] DeepSeek 冒烟验收通过
- [ ] 向用户报告实际结果并暂停，等待是否进入社区掉落率与复杂规划
- **状态：** pending

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

## 完成标准
- 不是仅有接口和空目录；每个里程碑必须具备可运行实现与测试。
- 外部服务无密钥或不可访问时，FakeModel、固定 Fixture 和最后快照仍可完成核心测试。
- 所有精确数字由确定性代码计算，模型只做意图与工具编排。
