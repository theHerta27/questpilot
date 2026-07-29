# 数据来源与许可边界

## Atlas Academy CN

- 版本：`/info` 与 `/raw/CN/info`
- 轻量角色索引：`/export/CN/basic_servant.json`
- 完整角色：`/export/CN/nice_servant.json` 或 `/nice/CN/servant/{collectionNo}`
- 材料：`/export/CN/nice_item.json`
- 章节关卡：`/export/CN/nice_war.json`
- 活动：`/export/CN/nice_event.json`

每份快照保存上游 hash、serverHash、dataVer、ETag、Last-Modified、抓取时间与 SHA-256。发布失败时数据库事务回滚；上游不可用时保留最后一份已验证快照。

## 社区掉落率

当前首版文件为 Chaldea 数据仓库的 `dist/dropData.json`，其上游说明来自 FGOアイテム効率劇場。

掉落率是社区观测数据，不属于 Atlas 事实。M3 只导入 10–20 个演示材料相关的永久自由关卡，排除活动、随机敌人与缺样本记录。版本清单必须固定仓库提交、`domusVer`、文件哈希与生成时间。

P1 固定版本清单：

- 仓库提交：`1d18e73b5b970fcf193335f29c645f654a142c69`
- 提交时间：`2026-07-29T15:01:19Z`
- `domusVer`：`1779642278`
- 文件 SHA-256：`e02dc69a9ef2e6a305d2e170effea43ba69b31e519d866160c3eead517caf50c`
- 实测结构：96 个物品、402 个关卡、2,435 条非零掉落率记录
- 许可状态：`unverified-local-only`

固定提交的完整仓库树中没有 `LICENSE`、`LICENCE` 或 `COPYING` 文件，因此不能推断存在再分发许可。原始文件只保存在 gitignored 本地缓存，不提交、不打包、不通过 API 提供下载；公开仓库只保存 Adapter、版本清单和合成 Fixture。页面必须标记“本地验证数据，不随项目再分发”。

## Mooncell

只保存已选页面的 URL、页面修订、抓取时间、许可说明和正文哈希。回答显示页面、章节、更新时间与支撑片段；页面不可用时使用最后一份已验证快照。
