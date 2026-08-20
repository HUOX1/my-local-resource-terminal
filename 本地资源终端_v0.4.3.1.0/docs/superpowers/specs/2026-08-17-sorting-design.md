# 影片排序设计

## 目标
在不改变扫描、播放、封面和档案语义的前提下，为海报墙和列表增加统一排序，并记住上一次排序设置。

## 排序项
- 最近添加（added_at）
- 编号（code）
- 标题（title）
- 发行日期（release_date）
- 评分（rating）
- 最后观看（last_watched_at）
- 观看次数（play_count）

每个排序项支持升序/降序。升级旧版本时默认保持“编号升序”。

## added_at
新增永久字段 `MovieMetadata.added_at`。首次建档时写入 UTC 时间，之后扫描不得修改。字段写入 metadata JSON 和 SQLite；旧 JSON 第一次读取时使用该 JSON 文件的修改时间作为迁移值并写回，确保后续数据库重建顺序稳定。

## UI
主窗口顶部增加排序下拉框和升/降序按钮。改变任一项立即刷新海报墙和列表，两者使用完全相同的结果。排序设置写入 settings.json 并在下次启动恢复。
