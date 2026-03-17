"""
Skill 3: Experiment Result Comparator

Inputs:
  - experiments: list of {name, config (optional), metrics: {metric: value}}
  - primary_metric: str (used for ranking)
  - higher_is_better: dict[str, bool] (default all True)
  - output_format: "json" | "latex" | "markdown" | "all" (default: "all")
  - caption / label: LaTeX table metadata
  - include_tradeoff: bool — include trade-off analysis text

Output:
  {
    "ranking": [...],
    "best_per_metric": {...},
    "tradeoff_analysis": "...",
    "latex_table": "...",
    "markdown_table": "...",
    "conclusions": [...]
  }
"""
from __future__ import annotations

from typing import Any

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.utils.latex_templates import generate_comparison_table
from sciskills.utils.llm_client import get_default_client


@registry.register
class ExperimentResultComparator(BaseSkill):
    name = "experiment_result_comparator"
    description = (
        "Compare multiple experiment results across metrics. "
        "Ranks models, identifies best/second-best per metric, "
        "generates LaTeX and Markdown comparison tables, "
        "and produces trade-off analysis text."
    )
    input_schema = {
        "type": "object",
        "required": ["experiments"],
        "properties": {
            "experiments": {
                "type": "array",
                "description": "List of experiment results.",
                "items": {
                    "type": "object",
                    "required": ["name", "metrics"],
                    "properties": {
                        "name": {"type": "string"},
                        "config": {"type": "object"},
                        "metrics": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                },
            },
            "primary_metric": {
                "type": "string",
                "description": "Primary metric used for ranking. If omitted, first metric key is used.",
            },
            "higher_is_better": {
                "type": "object",
                "description": "Map of metric name to bool. Default: all True (higher is better).",
                "additionalProperties": {"type": "boolean"},
            },
            "output_format": {
                "type": "string",
                "enum": ["json", "latex", "markdown", "all"],
                "default": "all",
            },
            "caption": {"type": "string", "default": "Experimental results."},
            "label": {"type": "string", "default": "tab:results"},
            "include_tradeoff": {
                "type": "boolean",
                "default": True,
                "description": "Generate trade-off analysis using LLM.",
            },
            "decimals": {"type": "integer", "default": 2},
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "ranking": {"type": "array"},
            "best_per_metric": {"type": "object"},
            "tradeoff_analysis": {"type": "string"},
            "latex_table": {"type": "string"},
            "markdown_table": {"type": "string"},
            "conclusions": {"type": "array"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        experiments: list[dict] = params["experiments"]
        if not experiments:
            return SkillResult.fail(errors=["No experiments provided."])

        # Collect all metric names
        all_metrics: list[str] = []
        for exp in experiments:
            for m in exp.get("metrics", {}):
                if m not in all_metrics:
                    all_metrics.append(m)

        primary_metric = params.get("primary_metric") or (all_metrics[0] if all_metrics else None)
        higher_is_better: dict[str, bool] = params.get("higher_is_better") or {
            m: True for m in all_metrics
        }
        decimals: int = params.get("decimals", 2)
        fmt: str = params.get("output_format", "all")

        # Ranking
        ranking = self._rank(experiments, primary_metric, higher_is_better)

        # Best per metric
        best_per_metric = self._best_per_metric(experiments, all_metrics, higher_is_better)

        # Conclusions (rule-based)
        conclusions = self._generate_conclusions(ranking, best_per_metric, all_metrics, higher_is_better)

        # LaTeX table
        latex_table = ""
        if fmt in ("latex", "all"):
            latex_table = generate_comparison_table(
                experiments=experiments,
                metrics=all_metrics,
                primary_metric=primary_metric,
                caption=params.get("caption", "Experimental results."),
                label=params.get("label", "tab:results"),
                higher_is_better=higher_is_better,
                decimals=decimals,
            )

        # Markdown table
        markdown_table = ""
        if fmt in ("markdown", "all"):
            markdown_table = self._generate_markdown_table(
                experiments, all_metrics, best_per_metric, higher_is_better, decimals
            )

        # Trade-off analysis (LLM)
        tradeoff_analysis = ""
        if params.get("include_tradeoff", True) and len(experiments) >= 2:
            tradeoff_analysis = self._tradeoff_analysis(
                experiments, all_metrics, best_per_metric, higher_is_better
            )

        return SkillResult.ok(
            data={
                "ranking": ranking,
                "best_per_metric": best_per_metric,
                "conclusions": conclusions,
                "latex_table": latex_table,
                "markdown_table": markdown_table,
                "tradeoff_analysis": tradeoff_analysis,
            }
        )

    # ------------------------------------------------------------------ #

    def _rank(
        self,
        experiments: list[dict],
        primary_metric: str | None,
        higher_is_better: dict[str, bool],
    ) -> list[dict]:
        if not primary_metric:
            return [{"rank": i + 1, "name": e["name"]} for i, e in enumerate(experiments)]

        hib = higher_is_better.get(primary_metric, True)
        scored = [
            (e, e.get("metrics", {}).get(primary_metric, float("-inf") if hib else float("inf")))
            for e in experiments
        ]
        scored.sort(key=lambda x: x[1], reverse=hib)

        return [
            {
                "rank": i + 1,
                "name": s[0]["name"],
                "primary_metric": primary_metric,
                "primary_value": s[1],
            }
            for i, s in enumerate(scored)
        ]

    def _best_per_metric(
        self,
        experiments: list[dict],
        metrics: list[str],
        higher_is_better: dict[str, bool],
    ) -> dict[str, dict]:
        result = {}
        for m in metrics:
            hib = higher_is_better.get(m, True)
            valid = [
                (e["name"], e.get("metrics", {}).get(m))
                for e in experiments
                if e.get("metrics", {}).get(m) is not None
            ]
            if not valid:
                continue
            valid.sort(key=lambda x: x[1], reverse=hib)
            result[m] = {
                "best_model": valid[0][0],
                "best_value": valid[0][1],
                "second_model": valid[1][0] if len(valid) > 1 else None,
                "second_value": valid[1][1] if len(valid) > 1 else None,
            }
        return result

    def _generate_conclusions(
        self,
        ranking: list[dict],
        best_per_metric: dict[str, dict],
        metrics: list[str],
        higher_is_better: dict[str, bool],
    ) -> list[str]:
        conclusions = []
        if ranking:
            top = ranking[0]
            conclusions.append(
                f"{top['name']} achieves the best overall performance"
                + (f" on {top.get('primary_metric', '')} ({top.get('primary_value', '')})" if top.get('primary_metric') else "")
                + "."
            )

        for m, info in best_per_metric.items():
            if info.get("second_model"):
                gap = None
                if isinstance(info["best_value"], (int, float)) and isinstance(info["second_value"], (int, float)):
                    gap = abs(info["best_value"] - info["second_value"])
                    gap_str = f" (gap: {gap:.4f})"
                else:
                    gap_str = ""
                conclusions.append(
                    f"On {m}: {info['best_model']} ({info['best_value']}) outperforms "
                    f"{info['second_model']} ({info['second_value']}){gap_str}."
                )

        return conclusions

    def _generate_markdown_table(
        self,
        experiments: list[dict],
        metrics: list[str],
        best_per_metric: dict[str, dict],
        higher_is_better: dict[str, bool],
        decimals: int,
    ) -> str:
        header = "| Model | " + " | ".join(metrics) + " |"
        sep = "|:---| " + " | ".join(["---:"] * len(metrics)) + " |"
        rows = [header, sep]

        for exp in experiments:
            cells = [exp["name"]]
            for m in metrics:
                v = exp.get("metrics", {}).get(m)
                if v is None:
                    cells.append("—")
                else:
                    formatted = f"{v:.{decimals}f}" if isinstance(v, float) else str(v)
                    if best_per_metric.get(m, {}).get("best_value") == v:
                        formatted = f"**{formatted}**"
                    elif best_per_metric.get(m, {}).get("second_value") == v:
                        formatted = f"_{formatted}_"
                    cells.append(formatted)
            rows.append("| " + " | ".join(cells) + " |")

        return "\n".join(rows)

    def _tradeoff_analysis(
        self,
        experiments: list[dict],
        metrics: list[str],
        best_per_metric: dict[str, dict],
        higher_is_better: dict[str, bool],
    ) -> str:
        """Use LLM to generate a concise trade-off analysis paragraph."""
        exp_summary = "\n".join(
            f"- {e['name']}: " + ", ".join(
                f"{m}={e.get('metrics',{}).get(m,'N/A')}" for m in metrics
            )
            for e in experiments
        )
        best_summary = "\n".join(
            f"- Best {m}: {info['best_model']} ({info['best_value']})"
            for m, info in best_per_metric.items()
        )

        prompt = f"""You are analyzing experimental results from a machine learning paper.
Given the following experiment data, write a concise 2-3 sentence trade-off analysis
that would be appropriate for inclusion in a paper's experiment section.
Focus on: which model wins overall, any notable trade-offs between metrics, and practical implications.

Experiments:
{exp_summary}

Best per metric:
{best_summary}

Write only the analysis paragraph, no headers."""

        try:
            llm = get_default_client()
            return llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
        except Exception as e:
            return f"[Trade-off analysis unavailable: {e}]"
