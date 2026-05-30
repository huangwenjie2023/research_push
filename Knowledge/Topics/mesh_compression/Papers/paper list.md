---
cssclasses: research-push-paper-list
---

# Paper List

```dataview
TABLE WITHOUT ID
  link(file.path, title) AS "论文",
  dateformat(date, "yyyy-MM-dd") AS "日期",
  read_status AS "状态",
  code AS "代码",
  choice(pdf_status = "downloaded", "已下载", pdf_status) AS "PDF",
  org AS "来源"
FROM "Knowledge/Topics/mesh_compression/Papers"
WHERE type = "paper_note"
SORT date DESC
```
