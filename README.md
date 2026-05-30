# research_push

这是一个文档优先的 Obsidian 研究工作台。你日常主要看 `Knowledge/`，自动推送系统、配置、缓存和脚本集中放在 `.system/`，可以在 Obsidian 里隐藏 `.system`。

项目级 Codex/agent 运行规则写在 `AGENTS.md`。以后总结、归档论文或更新 Obsidian 表格时，先遵守 `paper-archive-reader` skill 和 DB Folder 论文表格协议。

## 目录结构

```text
research_push/
  Knowledge/
    Daily/                         # 自动推送每日总览
    Topics/
      point_cloud_geometry_compression/
        Daily/                     # 点云压缩方向自动日报
        Papers/                    # 你的精读笔记
        Ideas/                     # 课题想法
        Experiments/               # 实验记录
      mesh_compression/
      rl_guided_generation/
    Papers/                        # 自动下载的本地 PDF
    Writing/                       # 综述、开题、论文、报告
    Synthesis/                     # 周报、月报、主题地图
    Feedback/                      # 阅读偏好和评分反馈

  .system/
    research_push/                 # 推送代码
    config/                        # 关键词、评分、LLM、source 配置
    scripts/                       # 本地定时脚本
    data/                          # SQLite 缓存，已忽略
    logs/                          # 运行日志，已忽略
```

## Quick Start

```powershell
cd E:\workshop\obsidian_file\research_push
Copy-Item .env.example .env
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
python -m research_push zotero-init
python -m research_push serve --host 127.0.0.1 --port 8765
```

## 自动推送输出

- `Knowledge/Daily/YYYY-MM-DD.md`：每日总览。
- `Knowledge/Topics/<topic>/Daily/YYYY-MM-DD.md`：每个方向的日报。
- `Knowledge/Papers/<topic>/`：公开 PDF 缓存，日报会链接到这里的本地 PDF。
- Zotero 轻量连接：默认只创建/确认 Zotero `Research Push` collection；需要时手动同步少量精选条目，并在日报写回 `zotero://select` 链接。
- `.system/data/research_push.sqlite3`：采集、评分、反馈、摘要缓存。

## 密钥

不要把任何 API key 写进仓库。请把 GitHub token、国内模型 key、Semantic Scholar/IEEE/X key 放入本地 `.env`。

如果曾经在聊天或日志中暴露 GitHub token，请先在 GitHub 中撤销并重新生成。
