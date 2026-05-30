# Codex Operating Rules

这份笔记给以后进入本 vault 的 Codex/agent 看，用来保持当前工作流一致。

## 论文归档结构

每篇论文放在对应方向的 `Papers/` 下，且每篇论文都是一个文件夹：

```text
Knowledge/Topics/<topic_id>/Papers/<paper_slug>/
  index.md
  paper.pdf
```

- `index.md` 是 Obsidian/Dataview 读取的论文笔记。
- `paper.pdf` 是真实本地 PDF；如果没有 PDF，`pdf_local` 写 `N/A`。
- 不要再使用 `Knowledge/Papers/` 作为集中 PDF 缓存。
- 其他日报、总览和材料只引用这个 paper 文件夹里的 PDF。

## Dataview 表格协议

每个方向的表格在：

```text
Knowledge/Topics/<topic_id>/Papers/paper list.md
```

不要手工维护表格行。新增论文时创建或更新对应 paper 文件夹里的 `index.md`，Dataview 会自动读取 frontmatter。

必备字段：

```yaml
type: "paper_note"
title:
date:
read_status: "未读"
org:
link:
code: "不知"
note:
url:
topic:
source_id:
doi:
arxiv_id:
pdf_status:
pdf_source:
pdf_local: "[本地 PDF](paper.pdf) | N/A"
score:
tags: [paper, research_push]
```

## 每日总结原则

- 直接信息源和最终溯源必须分开。
- 溯源规则以 `.system/research_push/provenance.py` 为准。
- 有本地 PDF 时必须保留本地 PDF 链接。
- 不绕过付费墙。
- 自动流程刷新 `index.md` 时，要保留用户写在 `## Reading Notes` 后面的内容。

## Zotero 原则

Zotero 暂时只保留访问权，未来可以作为信息源读取或摘数据；不要把它作为默认归档目标。

- 每日自动流程不写 Zotero。
- 用户明确要求时才访问或同步 Zotero。
- 如需写入 Zotero，沿用 add-only 策略：查重后只增加，不删除、不移动、不覆盖已有条目。
