---
database-plugin: basic
---

```yaml:dbfolder
name: paper list
description: Paper tracker with single-select dropdowns
columns:
  title:
    input: text
    accessorkey: title
    label: title
  date:
    input: calendar
    accessorkey: date
    label: date
  read_status:
    input: select
    accessorkey: read_status
    label: 是否读过
    options:
      - { label: "已读", value: "已读", color: "hsl(142, 45%, 55%)"}
      - { label: "未读", value: "未读", color: "hsl(36, 78%, 60%)"}
      - { label: "需要读", value: "需要读", color: "hsl(214, 72%, 58%)"}
  org:
    input: text
    accessorkey: org
    label: org
  link:
    input: text
    accessorkey: link
    label: link
  code:
    input: select
    accessorkey: code
    label: code
    options:
      - { label: "有", value: "有", color: "hsl(142, 45%, 55%)"}
      - { label: "无", value: "无", color: "hsl(0, 65%, 60%)"}
      - { label: "不知", value: "不知", color: "hsl(36, 78%, 60%)"}
  note:
    input: text
    accessorkey: note
    label: note
  url:
    input: text
    accessorkey: url
    label: url
```

