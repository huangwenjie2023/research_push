# Source Setup Guide

这里按优先级整理信息源。原则是先把免费、稳定、可溯源的源跑稳，再考虑付费或不稳定渠道。

## 1. 论文主源

### arXiv

- 成本：免费。
- 是否需要 key：不需要。
- 用途：第一时间发现预印本，尤其适合 AI/ML/graphics/compression。
- 当前状态：已启用。

### OpenAlex

- 成本：免费。
- 是否需要 key：不需要；建议配置邮箱以进入 polite pool。
- 用途：补充论文元数据、DOI、venue、开放 PDF 信息。
- 建议在 `.env` 配置：

```env
OPENALEX_MAILTO=你的邮箱
```

### Semantic Scholar

- 成本：免费起步。
- 是否需要 key：可选；配置 key 后更不容易限流。
- 用途：论文摘要、作者、开放 PDF、相关论文元数据。
- 建议在 `.env` 配置：

```env
SEMANTIC_SCHOLAR_API_KEY=你的key
```

## 2. 溯源补强

### Crossref

- 成本：免费。
- 是否需要 key：不需要；建议配置邮箱。
- 用途：从 DOI/publisher 角度补充最终出版源、会议/期刊、PDF link。
- 建议在 `.env` 配置：

```env
CROSSREF_MAILTO=你的邮箱
```

## 3. 代码与复现源

### GitHub

- 成本：免费。
- 是否需要 key：可选；配置 token 后搜索限额更高。
- 用途：代码仓库、复现项目、release、stars/language 等。
- 建议在 `.env` 配置：

```env
GITHUB_TOKEN=你的新token
```

注意：旧 token 如果曾经暴露，请先撤销再生成新的。

### Papers with Code

- 成本：免费。
- 是否需要 key：通常不需要。
- 用途：代码、任务、数据集、SOTA 表。
- 当前状态：配置中保留，但默认关闭；公共接口可能变化，后续确认稳定后再启用。

## 4. 社区与趋势源

### Hugging Face Papers

- 成本：免费。
- 是否需要 key：不需要。
- 用途：AI 社区热点论文、每日论文趋势。
- 当前状态：已启用。

### RSS

- 成本：免费。
- 是否需要 key：不需要。
- 用途：实验室博客、会议动态、Google Scholar Alert RSS、个人主页。
- 配置方式：在 `.system/config/sources.yaml` 增加 `type: rss` 的条目。

## 5. 可选付费源

### X

- 成本：通常需要付费或受限。
- 是否需要 key：需要 `X_BEARER_TOKEN`。
- 用途：作者首发、论文讨论、代码发布。
- 建议：先不用作主源，等免费源稳定后再考虑。

### IEEE

- 成本：通常需要 API key 或机构访问。
- 是否需要 key：需要 `IEEE_API_KEY`。
- 用途：正式出版论文、会议/期刊元数据。

## 推荐配置顺序

1. 配置 `OPENALEX_MAILTO` 和 `CROSSREF_MAILTO`，只需要你的邮箱。
2. 申请并配置 `SEMANTIC_SCHOLAR_API_KEY`，降低 429。
3. 生成新的 `GITHUB_TOKEN`，提高 GitHub 搜索限额。
4. 后续再评估 X、IEEE、SerpAPI 等付费源。

