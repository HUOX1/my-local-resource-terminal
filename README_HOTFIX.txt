G3 v0.6.1.9.2 parse hotfix

适用：已经覆盖 v0.6.1.9.2、启动时报 main.gd:314 top_color 未声明的版本。
用法：将本 ZIP 内容覆盖到 G3 源码根目录。
修复：删除 _build_ui() 中误插入的 top_color 主题刷新调用；正确的主题刷新仍保留在 _apply_theme()。
