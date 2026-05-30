from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Provenance:
    direct_label: str
    direct_url: str
    origin_label: str
    origin_url: str
    origin_note: str
    pdf_source_url: str
    pdf_status: str
    local_pdf_path: str

    @property
    def direct_markdown(self) -> str:
        return markdown_link(self.direct_label, self.direct_url)

    @property
    def origin_markdown(self) -> str:
        if self.origin_url:
            return markdown_link(self.origin_label, self.origin_url)
        return self.origin_note

    def summary_markdown(self) -> str:
        if self.direct_url == self.origin_url and self.direct_url:
            return f"{self.direct_markdown}；溯源：最终源头"
        return f"直接源：{self.direct_markdown}；溯源：{self.origin_markdown}"

    def local_pdf_markdown(self, note_path: Path) -> str:
        if self.pdf_status != "downloaded" or not self.local_pdf_path:
            return ""
        pdf_path = Path(self.local_pdf_path)
        if not pdf_path.exists():
            return ""
        relative = os.path.relpath(pdf_path, note_path.parent).replace("\\", "/")
        return markdown_link("本地 PDF", relative)

    def llm_sentence(self) -> str:
        origin = self.origin_markdown
        if self.origin_url:
            origin = f"论文/项目源头 {origin}"
        return f"直接信息源 {self.direct_markdown}；{origin}；PDF 状态：{self.pdf_status or 'not_fetched'}。"


def build_provenance(row) -> Provenance:
    source_id = row_get(row, "source_id") or "source"
    direct_url = row_get(row, "url")
    arxiv_id = row_get(row, "arxiv_id")
    doi = row_get(row, "doi")
    pdf_url = row_get(row, "pdf_url")
    pdf_status = row_get(row, "pdf_status") or "not_fetched"
    pdf_path = row_get(row, "pdf_path")

    if arxiv_id:
        arxiv_url = direct_url if "arxiv.org" in direct_url else f"https://arxiv.org/abs/{arxiv_id}"
        origin_label = "arXiv 最终源头"
        origin_url = arxiv_url
        origin_note = ""
    elif doi:
        origin_label = "DOI 最终源头"
        origin_url = f"https://doi.org/{doi}"
        origin_note = ""
    elif source_id == "arxiv":
        origin_label = "arXiv 最终源头"
        origin_url = direct_url
        origin_note = ""
    elif source_id == "github":
        origin_label = "GitHub 项目源头"
        origin_url = direct_url
        origin_note = ""
    elif pdf_url:
        origin_label = "PDF 可追溯源"
        origin_url = pdf_url
        origin_note = ""
    else:
        origin_label = ""
        origin_url = ""
        origin_note = "暂无更上游源头；使用直接信息源"

    return Provenance(
        direct_label=source_id,
        direct_url=direct_url,
        origin_label=origin_label,
        origin_url=origin_url,
        origin_note=origin_note,
        pdf_source_url=pdf_url,
        pdf_status=pdf_status,
        local_pdf_path=pdf_path,
    )


def row_get(row, key: str) -> str:
    try:
        if key in row.keys():
            value = row[key]
        else:
            value = ""
    except AttributeError:
        value = row.get(key, "") if isinstance(row, dict) else ""
    return str(value or "")


def markdown_link(label: str, url: str) -> str:
    return f"[{label}]({url})" if url else label

