# AGENTS.md

This repository is an Obsidian-based research workflow for daily literature monitoring, paper archiving, local PDF management, optional Zotero lookup, and writing feedback.

## Paper Archiving Rule

Use the local Codex skill when the user asks to archive, save, read, track, summarize, or organize a paper/project/link into this research system:

```text
C:\Users\huang\.codex\skills\paper-archive-reader
```

Topic slots:

- `point_cloud_geometry_compression`: AI point cloud geometry compression
- `mesh_compression`: AI mesh compression
- `rl_guided_generation`: reinforcement-learning-guided generation

If the target topic is unclear, ask the user to choose one of these three. If the target is obvious from the title, abstract, or user wording, proceed without asking.

## Paper Folder Protocol

Each real paper lives under its topic:

```text
Knowledge/Topics/<topic_id>/Papers/<paper_slug>/
  index.md
  paper.pdf        # optional, local only, ignored by git
```

The `<paper_slug>` format should stay close to the existing generated names:

```text
year_title-slug_arxiv-or-doi-or-id
```

Only `Knowledge/Topics/<topic_id>/Papers/<paper_slug>/paper.pdf` stores the real local PDF. Other notes should link to that file; do not create another PDF cache elsewhere in `Knowledge/`.

If a PDF is available, download it as `paper.pdf` in the paper folder. If no PDF is available, write `N/A` for the local PDF field.

## Dataview Table Protocol

Each topic has a Dataview table at:

```text
Knowledge/Topics/<topic_id>/Papers/paper list.md
```

This is not a manually maintained Markdown table. Do not manually edit rows in the table for ordinary paper archiving.

Every paper note must be:

```text
Knowledge/Topics/<topic_id>/Papers/<paper_slug>/index.md
```

and must include Dataview-readable frontmatter:

```yaml
---
type: "paper_note"
title: "<Paper Title>"
date: YYYY-MM-DD
read_status: "未读"
org: ""
link: ""        # direct information source
code: "不知"
note: ""
url: ""         # final/origin source
topic: "<topic_id>"
source_id: ""
doi: ""
arxiv_id: ""
pdf_status: "downloaded | unavailable | failed | not_fetched"
pdf_source: ""
pdf_local: "[本地 PDF](paper.pdf) | N/A"
score: 0.0
tags: [paper, research_push]
---
```

Valid `read_status` values: `已读`, `未读`, `需要读`.

Valid `code` values: `有`, `无`, `不知`.

## Daily Summary Rules

- Keep direct source and final provenance separate.
- Treat `.system/research_push/provenance.py` as the canonical implementation of provenance rules.
- Preserve local PDF links when available.
- Do not bypass paywalls.
- Keep `Knowledge/` human-facing and `.system/` automation-facing.
- Preserve user-written content under `## Reading Notes` in paper `index.md`.

## Zotero Policy

Zotero access may stay configured for future lookup or data extraction, but ordinary daily runs should not write to Zotero.

- Do not mutate Zotero during ordinary daily runs.
- Do not use Zotero as the default archive target.
- Only use Zotero when the user explicitly asks.
- If writing is explicitly requested, keep the old add-only policy: dedupe by DOI/arXiv/title, never delete, move, or overwrite existing Zotero items.

## Commands

Run project commands from the repository root:

```powershell
$env:PYTHONPATH = ".system"
python -m research_push daily
```

Manual local service:

```powershell
$env:PYTHONPATH = ".system"
python -m research_push serve --host 127.0.0.1 --port 8765
```

## Secrets And Git

- Never print or commit `.env`.
- `.env` contains local API keys and must stay ignored.
- `paper.pdf` files are local assets and must stay ignored by git.
- Preserve unrelated Obsidian edits.
- Commit generated notes only when the user asks to merge generated updates.
