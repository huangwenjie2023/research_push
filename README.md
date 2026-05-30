# research_push

面向长期博士研究的 Obsidian 知识库推送工具。它会围绕三个方向采集论文和项目，下载可公开访问的 PDF，按可解释评分排序，并生成每日 Markdown 笔记。

## Quick Start

```powershell
cd E:\workshop\obsidian_file\research_push
Copy-Item .env.example .env
python -m research_push daily
```

默认读取 `.env` 里的 `HTTP_PROXY` / `HTTPS_PROXY`，适配本机 `127.0.0.1:7890` 代理。

## 常用命令

```powershell
python -m research_push collect
python -m research_push fetch-pdf --date today --topic point_cloud_geometry_compression
python -m research_push rank --date today
python -m research_push summarize --date today --focus method_results
python -m research_push expand --topic mesh_compression --more 10
python -m research_push refresh --topic rl_guided_generation --query "diffusion reinforcement learning"
python -m research_push feedback --date today
python -m research_push serve --host 127.0.0.1 --port 8765
```

## 输出

- `notes/daily/YYYY-MM-DD.md`：每日总览。
- `notes/<topic>/YYYY-MM-DD.md`：每个方向的日报。
- `papers/<topic>/`：公开 PDF 缓存。
- `data/research_push.sqlite3`：采集、评分、反馈、摘要缓存。

## 密钥

不要把任何 API key 写进仓库。请把 GitHub token、国内模型 key、Semantic Scholar/IEEE/X key 放入本地 `.env`。

如果曾经在聊天或日志中暴露 GitHub token，请先在 GitHub 中撤销并重新生成。

