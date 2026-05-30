# Codex Operating Rules

这份笔记是给以后进入本 vault 的 Codex/agent 看的，用来避免时间久了忘记当前工作流。

## 必须记住的两个工作流

### 1. `paper-archive-reader`

当用户要归档、保存、阅读、总结、追踪一篇论文/项目/链接时，使用本地 skill：

```text
C:\Users\huang\.codex\skills\paper-archive-reader
```

该 skill 规定了三类归档目标：

- `point_cloud_geometry_compression`：AI 点云几何压缩
- `mesh_compression`：AI Mesh 压缩
- `rl_guided_generation`：强化学习引导生成模型

如果目标不明确，先问用户归到哪一类；如果标题或用户表述已经明确，就直接执行。

### 2. DB Folder 论文表格协议

每个方向的 `Papers/` 下都有 DB Folder 表格：

```text
Knowledge/Topics/<topic_id>/Papers/paper list.md
```

这不是普通 Markdown 表格。新增论文时不要手动改表格行，而是创建带 frontmatter 的论文笔记。DB Folder 会自动读取字段。

必备 frontmatter 字段：

```yaml
title:
date:
read_status: "未读"
org:
link:
code: "不知"
note:
url:
```

## 每日总结原则

- 直接信息源和最终溯源必须分开。
- 溯源规则以 `.system/research_push/provenance.py` 为准，不要在别的文件里临时重写一套判断逻辑。
- 有本地 PDF 时必须保留本地 PDF 链接。
- Zotero 默认轻量连接，不在每日自动流程里频繁批量写入。
- 需要 Zotero 时，用 `zotero-init` 或显式 `zotero-sync`。
