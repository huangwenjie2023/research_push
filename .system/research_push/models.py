from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Topic:
    id: str
    name: str
    directory: str
    daily_limit: int
    default_focus: str
    keywords: tuple[str, ...]
    expanded_keywords: tuple[str, ...]
    negative_keywords: tuple[str, ...]


@dataclass
class Item:
    topic_id: str
    source_id: str
    title: str
    url: str
    abstract: str = ""
    published_at: str = ""
    authors: list[str] = field(default_factory=list)
    venue: str = ""
    doi: str = ""
    arxiv_id: str = ""
    pdf_url: str = ""
    code_url: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def stable_key(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower()}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id.lower()}"
        return self.url.lower()


@dataclass
class RankedItem:
    item: Item
    score: float
    features: dict[str, float]
    reasons: list[str]


def parse_topics(config: dict) -> list[Topic]:
    topics = []
    for item in config.get("topics", []):
        topics.append(
            Topic(
                id=item["id"],
                name=item["name"],
                directory=item.get("directory", item["id"]),
                daily_limit=int(item.get("daily_limit", 5)),
                default_focus=item.get("default_focus", "method_results"),
                keywords=tuple(item.get("keywords", [])),
                expanded_keywords=tuple(item.get("expanded_keywords", [])),
                negative_keywords=tuple(item.get("negative_keywords", [])),
            )
        )
    return topics

