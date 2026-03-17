---
name: experiment-result-comparator
description: Compare multiple machine learning experiment results across metrics, generate publication-ready LaTeX (booktabs) and Markdown comparison tables, rank models, and produce a trade-off analysis paragraph. Use when a researcher has finished running experiments and needs to build a results table for a paper, identify which model wins on which metric, or understand accuracy-speed trade-offs. Do NOT use for statistical significance testing between experiments (use statistical-test-advisor for that), for comparing experiments from different tasks or datasets without noting the incompatibility, or when fewer than 2 models are provided.
---

# Experiment Result Comparator

Takes structured experiment results and produces publication-ready comparison tables and ranked analysis. **This skill performs descriptive comparison only** — it does not claim statistical significance. For significance testing, use `statistical-test-advisor` separately.

## Input Schema

```json
{
  "experiments": [
    {
      "name":    "string — model/system name",
      "config":  "object | null — hyperparameters or variant description",
      "metrics": {
        "<metric_name>": "number"
      }
    }
  ],
  "primary_metric":    "string | null — metric used for ranking (default: first metric)",
  "higher_is_better":  {"<metric_name>": "boolean"},
  "output_format":     "string — 'json' | 'latex' | 'markdown' | 'all' (default: 'all')",
  "caption":           "string — LaTeX table caption",
  "label":             "string — LaTeX \\label{} key",
  "include_tradeoff":  "boolean — default true: generate LLM trade-off analysis",
  "decimals":          "integer — decimal places for metric values (default: 2)",
  "note_significance": "boolean — default true: add a disclaimer that results are descriptive only"
}
```

**`experiments` is required and must contain at least 2 entries.**

## Output Schema

```json
{
  "ranking": [
    {
      "rank":            1,
      "name":            "string",
      "primary_metric":  "string",
      "primary_value":   0.0
    }
  ],
  "best_per_metric": {
    "<metric_name>": {
      "best_model":    "string",
      "best_value":    0.0,
      "second_model":  "string | null",
      "second_value":  0.0
    }
  },
  "pareto_optimal": ["string — model names on the Pareto frontier if 2+ metrics provided"],
  "conclusions": ["string — rule-generated factual statements"],
  "tradeoff_analysis":  "string — LLM paragraph (empty if include_tradeoff=false)",
  "significance_note":  "string — disclaimer about descriptive-only nature",
  "latex_table":        "string — booktabs LaTeX (empty if format != latex/all)",
  "markdown_table":     "string — GFM table (empty if format != markdown/all)"
}
```

### Table formatting conventions

- **Bold** (`\textbf{}`) = best value per metric column
- *Underline* (`\underline{}`) = second-best value per metric column
- Sorted by `primary_metric` descending (or ascending if `higher_is_better=false`)
- Requires `\usepackage{booktabs}` in LaTeX preamble

## When to Use

- User says "I finished running experiments, help me make a results table"
- User wants to compare multiple models/configurations on the same benchmark
- User needs a LaTeX table for their paper's Experiment section
- User wants to understand which metric each model excels at

## When NOT to Use

- **Statistical significance**: "Is Model A significantly better than B?" → use `statistical-test-advisor`
- **Cross-task comparison**: comparing models on different datasets without explicit caveats is misleading — add `note_significance=true` and state this in your response
- **Fewer than 2 models**: pointless to compare
- **Missing values**: if some models have `null` for critical metrics, note this prominently; do not silently skip rows

## Step-by-Step Instructions

1. **Collect experiment results** from the user. Required: model names + numeric metric values. Optional: hyperparameter configs.

2. **Clarify metric direction**: ask the user whether lower is better for any metric (e.g. latency, perplexity, error rate, FLOPs).

3. **Create the input JSON** at `/tmp/experiments.json` with the schema above.

4. **Run the script**:
   ```bash
   python skills/experiment-result-comparator/run.py --input /tmp/experiments.json

   # Faster (skip LLM trade-off):
   python skills/experiment-result-comparator/run.py --input /tmp/experiments.json --no-tradeoff
   ```

5. **Present results** in this order:
   a. **Markdown table** inline in the conversation (immediate readability)
   b. **LaTeX table** as a fenced code block (paste-ready for paper)
   c. **Ranking** by primary metric
   d. **Trade-off analysis** paragraph
   e. **Significance note**: always remind the user that this is descriptive comparison, not statistical testing

6. If the user asks "is this difference significant?" — redirect to `statistical-test-advisor` and explain that multiple runs with variance are needed.

## Known Limitations

- Comparison is purely descriptive. With a single run per model, no claim of statistical superiority can be made
- Pareto optimality only computed when exactly 2 metrics are provided
- Trade-off analysis is LLM-generated and may not be accurate for very domain-specific metrics (e.g. BLEU scores, medical F1)

For ablation study table format, see `docs/ablation-tables.md`.
