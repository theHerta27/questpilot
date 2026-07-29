# QuestPilot M1 验收加固报告

验收日期：2026-07-29  
范围：可运行性、真实 Atlas CN、角色纠错、多目标材料缺口、DeepSeek V4 Flash  
结论：通过；用户已完成手工评审，P0 封板后进入真实社区掉落率与受约束规划阶段。

## 1. 版本与安全基线

- 基线提交：`22cf03cd00c02de6742374e276bf8bbd031277b5`
- 基线标签：`m1-generated-baseline`
- `.env`、数据库、缓存、日志、PID、报告与 Atlas 原始快照均由 `.gitignore` 排除。
- 提交候选秘密模式扫描：0 个匹配文件。
- DeepSeek 密钥只从根目录 `.env` 的 `MODEL_API_KEY` 读取；前端、日志、Git 与测试 Fixture 不含真实密钥。

## 2. 启动验收

标准地址：

- Web：`http://127.0.0.1:5173/`
- API：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`

实测：

| 检查 | 结果 |
|---|---|
| `doctor.ps1` | uv、Node.js、npm、`.env`、前后端依赖、PostgreSQL 全部通过 |
| `start.ps1` | 约 6–7 秒内完成启动和双端健康检查，并打印标准地址 |
| Web | HTTP 200 |
| API `/health` | `status=ok`, `version=0.1.0` |
| `stop.ps1` | 只停止 `.runtime` 中记录的脚本托管 PID |

启动器使用脱离当前输出句柄的隐藏进程。此前“命令一直 Running”的根因是长期子进程继承了调用命令的输出句柄，并非 Vite 或 FastAPI 启动缓慢。

## 3. Atlas CN 真实数据

本次同步：

| 字段 | 实测值 |
|---|---|
| Atlas `hash` | `ec2a23` |
| `serverHash` | `6a6f74` |
| `dataVer` | `966` |
| 材料记录 | 1,870 |
| 已发布快照 | 5 |
| 页面展示 | 来源、区域、版本、dataVer、更新时间、来源链接 |

三名人工核对角色由 `basic_servant.json` 使用固定种子 `20260729` 随机抽取：

| collectionNo | 角色 | Atlas 每技能记录 | 公开资料核对 |
|---:|---|---:|---|
| 254 | 伊阿宋 | 9 个等级跃迁、14 条材料记录 | 逐级数量一致 |
| 262 | 刑部姬（Archer） | 9 个等级跃迁、14 条材料记录 | 逐级数量一致 |
| 324 | 雅克·德·莫莱（Foreigner） | 9 个等级跃迁、9 条材料记录 | 逐级数量一致 |

核对资料：

- [Atlas Academy FGO game data API](https://api.atlasacademy.io/)
- [Mooncell：伊阿宋](https://fgo.wiki/w/%E4%BC%8A%E9%98%BF%E5%AE%8B)
- [Mooncell：刑部姬（Archer）](https://fgo.wiki/w/%E5%88%91%E9%83%A8%E5%A7%AC%28Archer%29)
- [Mooncell：雅克·德·莫莱](https://fgo.wiki/w/%E9%9B%85%E5%85%8B%C2%B7%E5%BE%B7%C2%B7%E8%8E%AB%E8%8E%B1)
- [GamePress：Jacques de Molay](https://fgo.gamepress.gg/servant/jacques-de-molay)

抽样核对点：

- 伊阿宋：1→2 剑之辉石×2；8→9 巨人的戒指×6、真理之卵×4；9→10 传承结晶×1。
- 刑部姬（Archer）：4→5 弓之魔石×10、振荡火药×12；8→9 晓光炉心×9、祸罪之箭头×20。
- 雅克·德·莫莱：九段数量依次为 10、10、12、12、12、15、15、15、1，材料名称与公开表一致。

适配过程中发现并修复：Atlas 当前 `skillMaterials` 是三个主动技能共用、按起始等级 `1`–`9` 编号的升级表。旧适配器误把这些键当作技能编号，真实角色会出现空材料。修复后明确复制到技能 1、2、3，并增加真实形状 Fixture。

## 4. 搜索纠错与多目标

- 精确中文名、日文名和别名优先。
- 长自然语言中完整出现的唯一名称或别名仍按精确实体处理。
- 只有不存在精确命中时才返回模糊候选。
- 模糊候选与同名多候选不会自动选择，Agent 运行时也会阻止后续材料/缺口工具。
- 真实同名验证：查询“刑部姬”返回 No.189 Assassin 与 No.262 Archer，要求用户选择。
- 真实别名验证：“弓刑部”“水刑部”精确解析到 No.262；“杰森”精确解析到 No.254。

浏览器闭环实测：

1. 选择 Archer 刑部姬，加入技能一 1→6。
2. 通过别名“杰森”加入伊阿宋技能一 1→6。
3. 合并得到 8 类材料、零库存总缺口 97。
4. 删除伊阿宋目标后，目标数变为 1，旧缺口被清空。

同一角色同一技能的重复目标按“后一次完整覆盖前一次”处理；后一次可同时覆盖当前等级和目标等级，即使目标更低也以用户最后输入为准。前端更新原行，后端按最后输入再次去重。

## 5. 分层测试

### 确定性测试

| 套件 | 结果 |
|---|---|
| Ruff | 通过 |
| 后端 pytest | 34 通过，1 个可选在线契约测试跳过 |
| 材料缺口单元评测 `material-gap-unit-v1` | 50/50，pass_rate=1.0 |
| 前端 Vitest | 6/6 |
| 前端生产构建 | 通过，1,630 modules transformed |
| Playwright 桌面/移动与重复覆盖 E2E | 2/2 |

50 条减法用例只命名为“材料缺口单元评测”，不代表完整 Agent 评测。

### FakeModel 轨迹测试

结果：相关 Harness 测试 5/5；其中核心 FakeModel 轨迹场景 2/2。

- 预设 Tool Call 驱动 `get_skill_materials` 完整调用链。
- 模糊角色结果触发确定性中止，即使 FakeModel 同轮预设了后续材料工具，也只执行 `search_character`。
- 事件 sequence 严格递增，包含模型、工具、验证与运行闭合事件。

### DeepSeek V4 Flash 在线测试

配置：

- Base URL：`https://api.deepseek.com`
- Model：`deepseek-v4-flash`
- Thinking：显式 `disabled`
- 真实自然语言任务：12

P0 封板复验结果：12/12，通过率 100%；总耗时约 80.5 秒。

覆盖内容：

- 意图解析：身份查询、材料查询、库存缺口、多目标合并。
- 别名：杰森、弓刑部、水刑部、莫莱。
- 纠错：同名刑部姬、近似拼写“伊阿松”。
- 工具选择：`search_character`、`get_skill_materials`、`calculate_material_gap`。
- 工具参数：内部角色 ID、技能号、等级范围、多目标数量均通过 Pydantic。
- 最终解释：每条任务均非空并包含预期角色或材料事实。

正式报告保存在本机 gitignored 路径：
`reports/generated/deepseek-smoke-acceptance-20260729-final.json`。

DeepSeek 请求格式依据：

- [DeepSeek API：首次调用](https://api-docs.deepseek.com/zh-cn/)
- [DeepSeek API：Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)
- [DeepSeek API：Tool Calls](https://api-docs.deepseek.com/guides/tool_calls)

## 6. 阶段边界

M1 已封板；下一阶段已获批准，但仍保持以下边界：

- 真实社区掉落率接入或原始数据再分发；
- 全量/全局最优复杂规划；
- Mooncell 生产语料扩展；
- MCP 扩展；
- 云部署。
