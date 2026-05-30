---
type: "paper_note"
title: "Lossy Point Cloud Geometry Compression via End-to-End Learning"
date: 2019-09-26
read_status: "未读"
org: "IEEE transactions on circuits and systems for video technology (Print)"
link: "https://www.semanticscholar.org/paper/108bf3960211c76eb6d10fda63df2435fdec8008"
code: "不知"
note: ""
url: "https://arxiv.org/abs/1909.12037"
topic: "point_cloud_geometry_compression"
source_id: "semantic_scholar"
doi: "10.1109/TCSVT.2021.3051377"
arxiv_id: "1909.12037"
pdf_status: "downloaded"
pdf_source: "https://arxiv.org/pdf/1909.12037"
pdf_local: "[本地 PDF](../../../Papers/point_cloud_geometry_compression/2019_wang_lossy-point-cloud-geometry-compression-via-end-to-end-learning_1909.12037.pdf)"
zotero: "[zotero://select/library/items/D77XCDYQ](zotero://select/library/items/D77XCDYQ)"
score: 10.09
tags: [paper, research_push]
---

# Lossy Point Cloud Geometry Compression via End-to-End Learning

- Topic: [[../Daily/2026-05-30|AI 点云几何压缩 2026-05-30]]
- Score: 10.09
- Direct source: [semantic_scholar](https://www.semanticscholar.org/paper/108bf3960211c76eb6d10fda63df2435fdec8008)
- Final source: [arXiv 最终源头](https://arxiv.org/abs/1909.12037)
- PDF source: https://arxiv.org/pdf/1909.12037
- Local PDF: [本地 PDF](../../../Papers/point_cloud_geometry_compression/2019_wang_lossy-point-cloud-geometry-compression-via-end-to-end-learning_1909.12037.pdf)
- Code: Unknown
- Authors: Jianqiang Wang, Hao Zhu, Haojie Liu, Zhan Ma
- Zotero: [zotero://select/library/items/D77XCDYQ](zotero://select/library/items/D77XCDYQ)

## Summary

**方法/结果速览**：This paper presents a novel end-to-end Learned Point Cloud Geometry Compression (a.k.a., Learned-PCGC) system, leveraging stacked Deep Neural Networks (DNN) based Variational AutoEncoder (VAE) to efficiently compress the Point Cloud Geometry (PCG). In this systematic exploration, PCG is first voxelized, and partitioned into non-overlapped 3D cubes, which are then fed into stacked 3D convolutions for compact latent feature and hyperprior generation. Hyperpriors are used to improve the conditional

**可做方向联想**：先检查论文实验设置、数据集和开源情况；若训练规模不大，可尝试在 4x48G RTX 4090 上复现核心模块或做小规模消融。暂未发现代码链接。

**溯源**：直接信息源 [semantic_scholar](https://www.semanticscholar.org/paper/108bf3960211c76eb6d10fda63df2435fdec8008)；论文/项目源头 [arXiv 最终源头](https://arxiv.org/abs/1909.12037)；PDF 状态：downloaded。

## Reading Notes

