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

候选文件为 Chaldea 数据仓库的 `dist/dropData.json` 和 `wiki/domus_aurea_drop_sheet.csv`，其上游说明来自 FGOアイテム効率劇場。

掉落率是社区观测数据，不属于 Atlas 事实。M3 只导入 10–20 个演示材料相关的永久自由关卡，排除活动、随机敌人与缺样本记录。版本清单必须固定仓库提交、`domusVer`、文件哈希与生成时间。

`chaldea-data` 当前没有声明仓库级许可证，因此原始文件不得提交到公开仓库。导入前应完成许可审查。

## Mooncell

只保存已选页面的 URL、页面修订、抓取时间、许可说明和正文哈希。回答显示页面、章节、更新时间与支撑片段；页面不可用时使用最后一份已验证快照。
