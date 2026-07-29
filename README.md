# QuestPilot

QuestPilot 是一个可验证的复杂养成游戏规划 Agent 作品集项目。它把模型限制在意图解析与工具编排范围内，材料数量、库存缺口、体力与路线约束全部由确定性代码计算并再次验证。

当前实现覆盖原计划 M0–M6 的可运行纵切面：

- 渐进式 Harness：`ModelGateway`、`FakeModel`、`ToolSpec`、`ToolRegistry`、统一事件、预算、幂等重试、超时、循环检测、Checkpoint、Trace、Replay 输入包、Prompt Registry 与离线评测。
- M1 业务闭环：角色搜索、技能材料、库存替换/增量、材料需求与缺口。
- M2 数据管线：Atlas CN 的 fetch、快照、哈希、校验、适配与幂等发布。
- M3 局部规划：LangGraph 节点、固定版本社区掉落率、10–20 关候选边界、AP/时间约束、降级与 SSE。
- M4 RAG：Mooncell HTML 清洗、标题切分、离线哈希向量、混合检索与可追溯引用。
- M5/M6：Fallback Gateway、OTel、指标、Trace/Replay 页面、50 条评测、MCP 与虚构 RPG Adapter。

## 快速开始

本地演示默认使用 SQLite 和 FakeModel，不需要 API Key、Docker 或网络：

```powershell
cd backend
uv sync --extra dev
uv run questpilot-seed
uv run questpilot-api
```

另开终端：

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173`。如需 PostgreSQL，复制 `.env.example` 为 `.env` 并修改 `DATABASE_URL`；也可以运行 `docker compose up --build`。

## 验证

```powershell
cd backend
uv run ruff check src tests
uv run pytest
uv run questpilot-eval

cd ../frontend
npm test
npm run build
```

## 数据边界

Atlas CN 用于游戏实体、中文名、技能材料和关卡事实。掉落率来自独立的社区观测数据源，并保存版本、哈希、样本量与候选范围。由于 `chaldea-data` 仓库当前没有声明仓库级许可证，原始文件只允许进入 gitignored 缓存；公开仓库只提交适配器、版本清单模板与合成测试数据。

M3 输出仅声明固定候选集内的局部最优。未覆盖材料返回“无已验证路线”，不会猜测。

Redis 与 S3/MinIO 属于 M6 可选运行层。Compose 已提供服务；若在 Python
进程中启用对应 Adapter，额外安装 `redis` 与 `boto3`。核心阶段不会把它们作为前置条件。

更多说明见 [架构](docs/architecture.md)、[数据来源](docs/data-sources.md) 与 [演示脚本](docs/demo-script.md)。
