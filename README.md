# QuestPilot

QuestPilot 是一个可验证的复杂养成游戏规划 Agent 作品集项目。它把模型限制在意图解析与工具编排范围内，材料数量、库存缺口、体力与路线约束全部由确定性代码计算并再次验证。

当前开发冻结在“可运行性与 M1 验收加固”阶段；Mooncell、MCP、社区掉落率和云部署暂不继续扩展。仓库保留此前 M0–M6 纵切面代码，本阶段验收重点是：

- 固定的本地启动地址与健康检查脚本；
- 真实 Atlas CN 角色、技能材料、版本和来源；
- 精确名称/别名优先、模糊候选必须确认的角色解析；
- 多角色、多技能目标的添加、删除、重复目标合并和确定性缺口；
- 统一 Harness 下的 FakeModel 与 DeepSeek V4 Flash Tool Calling。

## 快速开始

标准本地地址为 `http://127.0.0.1:5173/`。推荐从项目根目录一键启动：

```powershell
.\scripts\doctor.ps1
.\scripts\start.ps1
```

`start.ps1` 会启动前后端、检查健康状态并打印标准地址。停止由脚本启动的进程：

```powershell
.\scripts\stop.ps1
```

首次运行前仍需安装依赖并初始化数据：

```powershell
cd backend
uv sync --extra dev
uv run questpilot-seed
cd ..\frontend
npm install
cd ..
```

复制 `.env.example` 为 `.env`，配置本机 PostgreSQL。DeepSeek 配置如下，密钥只填写在被 Git 忽略的 `.env` 中：

```dotenv
MODEL_PROVIDER=deepseek
MODEL_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=
MODEL_NAME=deepseek-v4-flash
MODEL_THINKING_ENABLED=false
```

同步本阶段使用的真实 Atlas CN 样本：

```powershell
cd backend
uv run questpilot-atlas --collection-no 254 262 324 189
cd ..
```

其中 254、262、324 是固定种子抽取的三名人工核对样本；189 用于验证“刑部姬”同名候选。

## 验证

```powershell
cd backend
uv run ruff check src tests
uv run pytest
uv run questpilot-eval

cd ../frontend
npm test
npm run build
npm run test:e2e
```

`questpilot-eval` 是 50 条“材料缺口单元评测”，不代表完整 Agent 评测。启动服务后可运行 12 条 DeepSeek 真实自然语言冒烟任务：

```powershell
cd ..
.\scripts\deepseek-smoke.ps1
```

## 数据边界

Atlas CN 用于游戏实体、中文名、技能材料和关卡事实。掉落率来自独立的社区观测数据源，并保存版本、哈希、样本量与候选范围。由于 `chaldea-data` 仓库当前没有声明仓库级许可证，原始文件只允许进入 gitignored 缓存；公开仓库只提交适配器、版本清单模板与合成测试数据。

M3 输出仅声明固定候选集内的局部最优。未覆盖材料返回“无已验证路线”，不会猜测。

Redis 与 S3/MinIO 属于 M6 可选运行层。Compose 已提供服务；若在 Python
进程中启用对应 Adapter，额外安装 `redis` 与 `boto3`。核心阶段不会把它们作为前置条件。

本阶段实测结果见 [M1 验收报告](docs/m1-acceptance-report.md)。更多说明见
[架构](docs/architecture.md)、[数据来源](docs/data-sources.md) 与
[演示脚本](docs/demo-script.md)。
