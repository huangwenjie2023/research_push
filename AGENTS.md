# AGENTS.md

This repository is an Obsidian-based research workflow for daily literature monitoring, paper archiving, Zotero lightweight linking, and writing feedback.

## Always Remember The Two Paper-Workflow Skills

When working in this repository, Codex should treat the following two workflow requirements as active project rules.

### 1. Use `paper-archive-reader` For Paper Archiving

Use the local Codex skill:

```text
C:\Users\huang\.codex\skills\paper-archive-reader
```

Use it whenever the user asks to archive, save, read, track, summarize, or organize a paper/project/link into this research system.

This includes requests such as:

- "归档这篇论文"
- "保存到点云压缩"
- "放到 Zotero"
- "下载 PDF 并写入 Obsidian"
- "这篇以后多推类似的"
- "把今天某方向前几条放进 Zotero"

The skill defines the current topic slots:

- `point_cloud_geometry_compression`: AI 点云几何压缩
- `mesh_compression`: AI Mesh 压缩
- `rl_guided_generation`: 强化学习引导生成模型

If a paper's target topic is unclear, ask the user to choose one of these three. If the target is obvious from the title, abstract, or user wording, proceed without asking.

### 2. Preserve The Obsidian DB Folder Paper Table Protocol

Each topic has a DB Folder table at:

```text
Knowledge/Topics/<topic_id>/Papers/paper list.md
```

This is not a normal Markdown table. It is an Obsidian DB Folder plugin table. Do not manually edit rows in the table for ordinary paper archiving.

Instead, every paper note created under:

```text
Knowledge/Topics/<topic_id>/Papers/
```

must include frontmatter fields that DB Folder can read:

```yaml
---
topic: <topic_id>
type: paper_note
title: "<Paper Title>"
date: YYYY-MM-DD
read_status: "未读"
org: ""
link: ""
code: "不知"
note: ""
url: ""
status: inbox
source: manual_or_auto
direct_source:
origin_source:
paper_url:
pdf_source:
local_pdf:
doi:
arxiv:
zotero:
citation_key:
tags:
  - research_push
  - paper
---
```

Valid `read_status` values:

- `已读`
- `未读`
- `需要读`

Valid `code` values:

- `有`
- `无`
- `不知`

## Daily Summary And Archive Rules

When generating or updating daily summaries:

- Keep direct source and final provenance separate.
- Treat `.system/research_push/provenance.py` as the canonical implementation of provenance rules. Do not reimplement source/origin/PDF-link logic ad hoc in exporters or summarizers.
- Preserve local PDF links when available.
- Do not bypass paywalls.
- Do not mutate Zotero during ordinary daily runs.
- Only use Zotero sync when the user explicitly asks, or when the command includes `--with-zotero`.
- Zotero sync is add-only. Use the single `research_push` collection by default, dedupe by DOI/arXiv/title, and never delete, move, or overwrite existing Zotero items.
- Keep `Knowledge/` human-facing and `.system/` hidden/automation-facing.

## Commands

Run project commands from the repository root:

```powershell
$env:PYTHONPATH = ".system"
python -m research_push daily
```

Manual Zotero collection initialization:

```powershell
$env:PYTHONPATH = ".system"
python -m research_push zotero-init
```

Manual, explicit Zotero sync for selected items:

```powershell
$env:PYTHONPATH = ".system"
python -m research_push zotero-sync --date today --topic <topic_id> --limit 1
```

## Secrets And Git

- Never print or commit `.env`.
- `.env` contains local API keys and must stay ignored.
- Preserve unrelated Obsidian edits.
- Commit generated notes only when the user asks to merge generated updates.
