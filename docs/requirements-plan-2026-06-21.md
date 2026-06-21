# QuickBid Requirements Plan - 2026-06-21

This plan organizes the 10 requested product changes into an implementation sequence. The goal is to move QuickBid from a mostly linear, keyword-driven workflow toward a state-aware multi-agent workbench with traceable evidence, independent tool actions, and bid-volume separation.

## Current Reading

QuickBid already has the main building blocks: `ParserAgent`, `MatcherAgent`, `GeneratorAgent`, `ReviewerAgent`, `SubBidAgent`, a FastAPI chat/SSE router, and a Next.js tool-result UI. The weak points are the contracts between stages:

- The chat router still behaves like a keyword router for several actions.
- Parsed data has partial page evidence, but downstream UI and agents do not use a unified evidence model.
- Outline, material matching, generation, review, and export are still biased toward one linear main-bid flow.
- Reviewer output depends heavily on LLM judgment and does not yet locate issues precisely in tender requirements and generated draft content.

## Requirement Map

| No. | Requirement | Primary Area | Priority |
| --- | --- | --- | --- |
| 1 | Natural-language control after tender upload | Chat router / Orchestrator | P0 |
| 2 | Parser report marker/risk display improvements | Frontend parser report | P0 |
| 3 | Click report content to show source page | Parser schema / report UI | P1 |
| 4 | Support parsed-data supplement and correction | API / QAAgent / audit trail | P1 |
| 5 | Separate commercial and technical bids during outline/material generation | Matcher / Generator / file tree | P1 |
| 6 | Export outline with two-level catalog and scoring/requirement source | Matcher / export endpoint | P1 |
| 7 | Match tender templates and requirements, not only reusable materials | Matcher source model | P1 |
| 8 | Reviewer must provide precise judgments and locations | Reviewer / frontend review UI | P2 |
| 9 | Independent agent tools with data/state readiness checks | Tool registry / chat router | P2 |
| 10 | Markdown file preview cannot close/back | Next route handling | P0 |

## Phase 0 - Low-Risk UX Fixes

Scope:

- Replace the upload follow-up phrase from "放好了" to a natural action such as "开始解析招标文件".
- Keep old phrases compatible, but trigger parsing from natural descriptions when the project is in `parsing`.
- Improve risk display so long text and alternate field names render fully.
- Rename the marker tab to clarify that it is currently statistical.
- Fix Markdown preview close behavior by using the Next router to remove `file` and `tender` query params.

Verification:

- Backend unit tests for parse-intent detection.
- `python -m py_compile main.py orchestrator.py`
- Existing focused tests around export/review where touched behavior may interact.
- `npx tsc --noEmit` in `web-next` if local dependencies are present.

## Phase 1 - Evidence Model

Introduce a shared evidence shape for parsed facts and downstream requirements:

```json
{
  "page": 12,
  "quote": "原文片段",
  "field_path": "scoring.dimensions[0].sub_items[2]",
  "source_type": "tender",
  "confidence": "high"
}
```

Apply it first as a compatibility layer around existing `source_page`, `source_pages`, `raw_text`, and `marker_extractions`. Do not require a full parser rewrite before the UI can consume evidence.

Deliverables:

- Evidence helper functions in the parser or a small service module.
- Parser report click target for K fields and risk items.
- Evidence panel showing page number, original quote, and JSON field path.

## Phase 2 - Parsed-Data Corrections

Add a structured correction path for extracted tender data.

Backend:

- `PATCH /projects/{project_id}/parsed-data`
- Accept explicit field patches for K fields and selected module paths.
- Store `_corrections` inside `parsed_data` with old value, new value, timestamp, source, and note.
- Let `QAAgent` or a lightweight parser convert natural language corrections into patch proposals.

Frontend:

- Allow "预算应为 900 万" and similar chat corrections after parsing.
- Surface correction confirmation in the parser report.

## Phase 3 - Commercial / Technical Volume Split

Extend outline chapter schema:

```json
{
  "id": "ch1",
  "no": 1,
  "title": "资格证明文件",
  "volume": "commercial",
  "category": "01_公司资质",
  "subsections": [],
  "source": "k12",
  "requirement_refs": [],
  "scoring_refs": []
}
```

Supported `volume` values:

- `commercial`
- `technical`
- `price`
- `other`

Impacted modules:

- `MatcherAgent.generate_outline()`
- `OutlineToolResult`
- `GeneratorAgent`
- tender file tree and export layout

## Phase 4 - Outline Export

Add outline-stage export before draft generation.

Output content:

- Two-level catalog.
- Volume and material category.
- Scoring item references.
- Tender template / requirement references with source pages.

Endpoint:

- `POST /projects/{project_id}/outline/export`

Initial formats:

- Markdown first.
- Word after the Markdown structure is stable.

## Phase 5 - Template and Requirement Matching

Upgrade material matching from "filesystem materials only" to multi-source matching.

Source types:

- `material_library`: reusable company materials from `materials/`
- `tender_template`: tender-provided form/template requirements
- `tender_requirement`: qualification, rejection, technical, commercial requirements
- `scoring_requirement`: scoring dimensions and sub-items

Match output should move toward:

```json
{
  "chapter_id": "ch3",
  "matched_sources": [
    {"source_type": "material_library", "title": "售后服务方案", "file_path": "..."},
    {"source_type": "scoring_requirement", "title": "售后服务与运维方案 3 分", "evidence": []}
  ]
}
```

Keep old `file_path`, `material_title`, and `match_score` during migration so `GeneratorAgent` and the current UI do not break.

## Phase 6 - Independent Agent Tool Readiness

Create a shared readiness layer. Each tool declares required project data and recoverable next actions.

Examples:

| Tool | Required Data | Recoverable Action |
| --- | --- | --- |
| `parseTender` | tender file exists | ask user to upload |
| `designOutline` | parsed data exists | run parser |
| `matchMaterials` | parsed data + outline | generate outline |
| `generateTender` | confirmed outline + matched chapters | run matcher |
| `reviewTender` | tender draft path | run generator |
| `exportOutline` | outline | generate outline |
| `exportTender` | tender draft path | run generator |

This should gradually replace scattered keyword/status checks in `main.py`.

## Phase 7 - Reviewer Evidence and Deterministic Checks

Split review into deterministic checks plus LLM semantic review.

Deterministic checks:

- Missing required chapters or subsections.
- Uncovered K10/K11 fatal and critical items.
- `[待补充:...]` placeholders.
- Amount, date, project name, tender number inconsistencies.
- Missing deviation table when K13 requires one.
- Commercial/technical volume mismatch.

Issue schema:

```json
{
  "check_id": "C08_星标项覆盖",
  "severity": "fail",
  "requirement_ref": {"page": 42, "quote": "★ 必须提供..."},
  "draft_ref": {"path": "main/technical/03_技术方案.md", "heading": "系统架构"},
  "problem": "未覆盖星标要求",
  "expected": "响应并提供证明材料",
  "actual": "未找到对应内容",
  "suggestion": "在技术方案中新增...",
  "blocking": true
}
```

Frontend review should show issue location first, not only counts.

## Implementation Order

1. Phase 0: finish low-risk fixes and tests.
2. Phase 1: evidence compatibility layer.
3. Phase 2: parsed-data correction API and chat correction flow.
4. Phase 3: outline `volume` split.
5. Phase 4: outline export.
6. Phase 5: multi-source matching.
7. Phase 6: tool readiness registry.
8. Phase 7: reviewer evidence and deterministic checks.

## Notes

- Do not remove existing keyword commands; keep them as shortcuts.
- Keep compatibility fields until generator/reviewer are fully migrated.
- Avoid large schema rewrites without adapter functions and tests.
- Runtime artifacts, tender files, materials with sensitive content, and generated exports must remain out of git except placeholders.
