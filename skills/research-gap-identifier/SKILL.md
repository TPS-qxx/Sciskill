---
name: research-gap-identifier
description: Analyze a collection of structured paper extractions to identify research gaps by type (task, data, method, evaluation, deployment, theoretical), ranked by evidence strength and gap confidence. Use after running paper-structural-extractor on 5+ papers when the user wants to find unexplored research directions, characterize the literature landscape for a Related Work section, or brainstorm thesis topics. Do NOT use with fewer than 5 papers (results are unreliable), when papers span unrelated tasks (apples-to-oranges comparison), or when the user needs systematic-review-grade evidence synthesis (this skill is exploratory, not exhaustive).
---

# Research Gap Identifier

Analyzes structured paper data to identify typed research gaps with evidence, build a coverage matrix across methods × datasets × tasks, and generate actionable research directions. Every identified gap carries a `gap_type`, supporting evidence from papers, and a `confidence` score.

**This skill performs exploratory gap analysis only.** It is not a substitute for a systematic literature review. For publication-quality gap claims, verify findings manually against the full paper set.

---

## Input Schema

```json
{
  "papers": [
    {
      "title":       "string",
      "year":        "string | null",
      "methodology": {
        "approach":        "string",
        "key_techniques":  ["string"]
      },
      "datasets":    [{"name": "string", "domain": "string | null"}],
      "metrics":     [{"name": "string"}],
      "limitations": ["string"],
      "future_work": ["string"],
      "research_question": {"value": "string", "confidence": 0.0}
    }
  ],
  "topic":                  "string — the field or task being analyzed (e.g. 'named entity recognition')",
  "min_papers":             "integer — minimum paper count for reliable analysis (default: 5, warn if < 5)",
  "gap_types":              ["task_gap | data_gap | method_gap | evaluation_gap | deployment_gap | theoretical_gap"],
  "min_coverage_threshold": "number — fraction below which a combination is flagged (default: 0.3)",
  "max_gaps":               "integer — max gaps to return, sorted by confidence (default: 10)",
  "include_directions":     "boolean — generate LLM research directions (default: true)",
  "include_matrix":         "boolean — include full coverage matrix (default: true)"
}
```

**`papers` and `topic` are required. `papers` must contain at least 5 entries; a warning is issued for < 15.**

### Gap type taxonomy

| Gap type | Description | Example |
|----------|-------------|---------|
| `task_gap` | The method exists but has never been applied to this task | RLHF fine-tuning never tested on low-resource MT |
| `data_gap` | No benchmark or dataset covers this domain or condition | No clinical NER dataset with negation annotation |
| `method_gap` | No method addresses a known challenge | No approach handles code-switching in sentiment analysis |
| `evaluation_gap` | A claim is made but no metric captures it | Efficiency claims without FLOPs or latency measurement |
| `deployment_gap` | Works in lab but untested in production conditions | Model accuracy not evaluated on noisy OCR input |
| `theoretical_gap` | Empirical results exist but no theoretical explanation | Attention heads show specialization pattern with no formal analysis |

---

## Output Schema

```json
{
  "summary": {
    "papers_analyzed":      0,
    "unique_methods":       0,
    "unique_datasets":      0,
    "unique_tasks":         0,
    "gaps_found":           0,
    "confidence_level":     "exploratory | moderate | strong",
    "coverage_warning":     "string | null — e.g. 'Only 7 papers: treat results as preliminary'"
  },
  "gaps": [
    {
      "gap_id":             "string — e.g. 'gap_001'",
      "gap_type":           "task_gap | data_gap | method_gap | evaluation_gap | deployment_gap | theoretical_gap",
      "description":        "string — plain-language description of the gap",
      "supporting_papers":  [
        {
          "title":    "string",
          "year":     "string | null",
          "evidence": "string — quoted or paraphrased text from paper supporting this gap"
        }
      ],
      "missing_combination": {
        "method":   "string | null",
        "dataset":  "string | null",
        "task":     "string | null"
      },
      "confidence":         0.0,
      "actionable_direction": "string — one concrete research direction addressing this gap"
    }
  ],
  "coverage_matrix": {
    "methods_x_datasets": {"<method>": {"<dataset>": 0.0}},
    "methods_x_tasks":    {"<method>": {"<task>": 0.0}},
    "zero_coverage_pairs": [["method", "dataset"]]
  },
  "trend_analysis":        "string — LLM paragraph: dominant methods, temporal shifts, converging paradigms",
  "suggested_directions":  [
    {
      "title":       "string — short name",
      "rationale":   "string — why this direction is promising",
      "gap_ids":     ["string — which gaps it addresses"],
      "feasibility": "high | medium | low",
      "novelty":     "high | medium | low"
    }
  ],
  "warnings": ["string — e.g. 'Low paper count: results may not generalize'"]
}
```

### Confidence scale (gap-level)

| Range | Meaning |
|-------|---------|
| 0.9–1.0 | Multiple papers explicitly state this gap; zero coverage confirmed |
| 0.7–0.9 | At least one paper names the gap; coverage < threshold |
| 0.5–0.7 | Inferred from coverage matrix; no paper explicitly names it |
| < 0.5 | Speculative; present as suggestion only |

### Summary `confidence_level`

| Level | Papers | Condition |
|-------|--------|-----------|
| `exploratory` | 5–14 | Treat as preliminary; high variance |
| `moderate` | 15–29 | Reasonable basis for hypothesis generation |
| `strong` | 30+ | Suitable for Related Work gap claims |

---

## When to Use

- User has structured data for 5+ papers from `paper-structural-extractor` (or manually formatted)
- User wants to find unexplored method-dataset combinations
- User is writing a Related Work section and needs to characterize literature coverage
- User is brainstorming research directions or thesis topics

## When NOT to Use

- **Fewer than 5 papers**: coverage matrix is meaningless, do not run — ask the user to extract more papers first
- **Papers from different tasks/fields without a unifying topic**: cross-task comparison produces misleading gaps — require a single `topic` string that applies to all papers
- **Need systematic-review-grade conclusions**: this skill is heuristic and exploratory; for meta-analysis or Cochrane-style synthesis, use dedicated systematic review tools
- **No `methodology`, `datasets`, or `limitations` fields available**: if paper extraction was `metadata`-only, skip this skill — the coverage matrix cannot be built

---

## Step-by-Step Instructions

1. **Ensure sufficient paper coverage**: the user must have at least 5 extracted papers. Recommend `paper-structural-extractor` with `mode=full` for best results.

2. **Combine paper JSONs** into a single input file:
   ```bash
   python skills/research-gap-identifier/merge_papers.py \
     /tmp/paper1.json /tmp/paper2.json /tmp/paper3.json \
     --topic "named entity recognition" \
     > /tmp/papers.json
   ```

3. **Run gap analysis**:
   ```bash
   # Full analysis (all gap types):
   python skills/research-gap-identifier/run.py --input /tmp/papers.json

   # Targeted: only method and data gaps:
   python skills/research-gap-identifier/run.py \
     --input /tmp/papers.json \
     --gap-types method_gap data_gap

   # Skip LLM directions (faster, deterministic only):
   python skills/research-gap-identifier/run.py \
     --input /tmp/papers.json --no-directions
   ```

4. **Check `summary.coverage_warning`** — if paper count is below 15, always surface this to the user.

5. **Present results** in this order:
   a. `summary` (paper count, gaps found, confidence level + warning if any)
   b. Top gaps sorted by `confidence` (show gap type tag, description, supporting evidence)
   c. `suggested_directions` (feasibility + novelty rating)
   d. `coverage_matrix` (optional, for power users)
   e. `trend_analysis` paragraph (suitable for Related Work intro)

6. **For gaps with `confidence < 0.6`**: qualify as "possibly" or "may represent" — do not state as fact.

7. **If the user asks "Is this gap novel enough to publish on?"** — explain that this skill identifies structural gaps, not competitive novelty. The user must verify via Google Scholar / Semantic Scholar that no recent unpublished preprints address the gap.

---

## Known Limitations

- Coverage matrix quality depends entirely on `paper-structural-extractor` output quality. Papers extracted in `metadata` mode only will not have sufficient fields
- Gap detection is structural (coverage-based), not semantic — two methods described differently may be the same approach
- `theoretical_gap` and `deployment_gap` types rely on LLM inference and have lower reliability than `task_gap` or `data_gap`
- Survey and position papers in the input set will inflate `methodology.approach` variety without reflecting actual empirical work — filter these out before running

For the complete gap type definitions and scoring rules, see `docs/gap-taxonomy.md`.
