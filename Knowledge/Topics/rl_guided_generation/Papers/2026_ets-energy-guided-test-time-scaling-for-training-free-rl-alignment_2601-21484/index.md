---
type: "paper_note"
title: "ETS: Energy-Guided Test-Time Scaling for Training-Free RL Alignment"
date: 2026-01-29
read_status: "未读"
org: "arXiv.org"
link: "https://www.semanticscholar.org/paper/27ed2d2304de18e4819e7a673ee01331ef7bf55c"
code: "不知"
note: ""
url: "https://arxiv.org/abs/2601.21484"
topic: "rl_guided_generation"
source_id: "semantic_scholar"
doi: "10.48550/arXiv.2601.21484"
arxiv_id: "2601.21484"
pdf_status: "unavailable"
pdf_source: ""
pdf_local: "N/A"
score: 6.67
tags: [paper, research_push]
---

# ETS: Energy-Guided Test-Time Scaling for Training-Free RL Alignment

- Topic: [[../../Daily/2026-05-30|强化学习引导生成模型 2026-05-30]]
- Score: 6.67
- Direct source: [semantic_scholar](https://www.semanticscholar.org/paper/27ed2d2304de18e4819e7a673ee01331ef7bf55c)
- Final source: [arXiv 最终源头](https://arxiv.org/abs/2601.21484)
- PDF source: N/A
- Local PDF: N/A
- Code: Unknown
- Authors: Xiu‐Qing Li, Jinkai Zhang, Mingyang Yi, Yu Li, Long Wang, Yue Wang, Ju Fan

## Summary

**方法/结果速览**：Reinforcement Learning (RL) post-training alignment for language models is effective, but also costly and unstable in practice, owing to its complicated training process. To address this, we propose a training-free inference method to sample directly from the optimal RL policy. The transition probability applied to Masked Language Modeling (MLM) consists of a reference policy model and an energy term. Based on this, our algorithm, Energy-Guided Test-Time Scaling (ETS), estimates the key energy t

**可做方向联想**：先检查论文实验设置、数据集和开源情况；若训练规模不大，可尝试在 4x48G RTX 4090 上复现核心模块或做小规模消融。暂未发现代码链接。

**溯源**：直接信息源 [semantic_scholar](https://www.semanticscholar.org/paper/27ed2d2304de18e4819e7a673ee01331ef7bf55c)；论文/项目源头 [arXiv 最终源头](https://arxiv.org/abs/2601.21484)；PDF 状态：unavailable。

## Reading Notes

