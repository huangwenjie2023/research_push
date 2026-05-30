# research_push

这是一个文档优先的 Obsidian 研究工作台。日常主要看 `Knowledge/`；自动推送系统、配置、缓存和脚本集中放在 `.system/`，可以在 Obsidian 里隐藏。

项目级 Codex/agent 规则写在 `AGENTS.md`。以后总结、归档论文或更新 Obsidian 表格时，遵守 `paper-archive-reader` skill 和 Dataview 论文表格协议。

## 目录结构

```text
research_push/
  Knowledge/
    Daily/                         # 每日总览
    Topics/
      point_cloud_geometry_compression/
        Daily/                     # 方向日报
        Papers/
          paper list.md            # Dataview 表格
          <paper_slug>/
            index.md               # 论文笔记
            paper.pdf              # 可选，本地 PDF，git 忽略
        Ideas/
        Experiments/
      mesh_compression/
      rl_guided_generation/
    Writing/
    Synthesis/
    Feedback/
    Overall/
  .system/
    research_push/                 # 推送代码
    config/                        # 关键词、评分、LLM、source 配置
    scripts/
    data/                          # SQLite 缓存，git 忽略
    logs/                          # 运行日志，git 忽略
```

真实 PDF 只放在：

```text
Knowledge/Topics/<topic_id>/Papers/<paper_slug>/paper.pdf
```

其他位置只写链接。如果没有 PDF，本地 PDF 字段写 `N/A`。

## Quick Start

```powershell
cd E:\workshop\obsidian_file\research_push
$env:PYTHONPATH = ".system"
python -m research_push daily
```

默认读取 `.env` 里的 `HTTP_PROXY` / `HTTPS_PROXY`，适配本机 `127.0.0.1:7890` 代理。

## 常用命令

```powershell
$env:PYTHONPATH = ".system"
python -m research_push collect
python -m research_push fetch-pdf --date today --topic point_cloud_geometry_compression
python -m research_push rank --date today
python -m research_push summarize --date today --focus method_results
python -m research_push expand --topic mesh_compression --more 10
python -m research_push refresh --topic rl_guided_generation --query "diffusion reinforcement learning"
python -m research_push feedback --date today
python -m research_push serve --host 127.0.0.1 --port 8765
```

Zotero 访问权可以保留，用于以后读取或摘数据；默认日常流程不写 Zotero，也不把 Zotero 当归档目标。

## 密钥

不要把任何 API key 写进仓库。GitHub token、国内模型 key、Semantic Scholar/IEEE/X key、Zotero key 都放在本地 `.env`。

如果曾经在聊天或日志中暴露 GitHub token，请先在 GitHub 撤销并重新生成。
