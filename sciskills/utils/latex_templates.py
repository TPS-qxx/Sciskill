"""
LaTeX table generation utilities for experiment comparison tables.
Follows common NLP/CV conference paper formatting conventions.
"""
from __future__ import annotations

from typing import Any


def format_value(v: Any, decimals: int = 2) -> str:
    """Format a metric value for LaTeX display."""
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def generate_comparison_table(
    experiments: list[dict],
    metrics: list[str],
    primary_metric: str | None = None,
    caption: str = "Experimental results.",
    label: str = "tab:results",
    highlight_best: bool = True,
    highlight_second: bool = True,
    higher_is_better: dict[str, bool] | None = None,
    decimals: int = 2,
) -> str:
    """
    Generate a LaTeX booktabs comparison table.

    Args:
        experiments: list of {"name": str, "metrics": {metric: value, ...}}
        metrics: ordered list of metric column names
        primary_metric: metric used to sort rows (descending by default)
        caption: table caption
        label: LaTeX label
        highlight_best: bold the best value per metric
        highlight_second: underline the second-best value per metric
        higher_is_better: dict mapping metric name to bool (default True for all)
        decimals: decimal places for float values

    Returns:
        LaTeX table string.
    """
    if higher_is_better is None:
        higher_is_better = {m: True for m in metrics}

    # Sort by primary metric if given
    if primary_metric and primary_metric in metrics:
        reverse = higher_is_better.get(primary_metric, True)
        experiments = sorted(
            experiments,
            key=lambda e: e.get("metrics", {}).get(primary_metric, float("-inf")),
            reverse=reverse,
        )

    # Find best and second-best per metric
    best: dict[str, Any] = {}
    second: dict[str, Any] = {}

    for m in metrics:
        values = [
            (i, e.get("metrics", {}).get(m))
            for i, e in enumerate(experiments)
            if e.get("metrics", {}).get(m) is not None
        ]
        if not values:
            continue
        hib = higher_is_better.get(m, True)
        sorted_vals = sorted(values, key=lambda x: x[1], reverse=hib)
        if sorted_vals:
            best[m] = sorted_vals[0][1]
        if len(sorted_vals) > 1:
            second[m] = sorted_vals[1][1]

    def cell(v: Any, m: str) -> str:
        formatted = format_value(v, decimals)
        if highlight_best and best.get(m) == v:
            return f"\\textbf{{{formatted}}}"
        if highlight_second and second.get(m) == v:
            return f"\\underline{{{formatted}}}"
        return formatted

    # Build LaTeX
    num_cols = 1 + len(metrics)
    col_spec = "l" + "c" * len(metrics)

    lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\toprule",
        "    Model & " + " & ".join(metrics) + " \\\\",
        "    \\midrule",
    ]

    for exp in experiments:
        row_vals = [exp.get("name", "—")]
        for m in metrics:
            v = exp.get("metrics", {}).get(m)
            if v is None:
                row_vals.append("—")
            else:
                row_vals.append(cell(v, m))
        lines.append("    " + " & ".join(row_vals) + " \\\\")

    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]

    return "\n".join(lines)


def generate_ablation_table(
    experiments: list[dict],
    component_cols: list[str],
    metrics: list[str],
    caption: str = "Ablation study.",
    label: str = "tab:ablation",
    checkmark: str = r"\checkmark",
    crossmark: str = "—",
    decimals: int = 2,
) -> str:
    """
    Generate an ablation study table with checkmark/cross for components.

    Args:
        experiments: list of {"name": str, "components": {col: bool}, "metrics": {metric: val}}
        component_cols: list of component column names
        metrics: list of metric column names
    """
    num_cols = 1 + len(component_cols) + len(metrics)
    col_spec = "l" + "c" * len(component_cols) + "c" * len(metrics)

    header = "    Model & " + " & ".join(component_cols + metrics) + " \\\\"

    lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\toprule",
        header,
        "    \\midrule",
    ]

    for exp in experiments:
        row_vals = [exp.get("name", "—")]
        for c in component_cols:
            row_vals.append(
                checkmark if exp.get("components", {}).get(c) else crossmark
            )
        for m in metrics:
            v = exp.get("metrics", {}).get(m)
            row_vals.append(format_value(v, decimals) if v is not None else "—")
        lines.append("    " + " & ".join(row_vals) + " \\\\")

    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]

    return "\n".join(lines)
