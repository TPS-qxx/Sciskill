"""Tests for ExperimentResultComparator — no LLM required."""
import pytest
from unittest.mock import patch

from sciskills.skills.experiment_comparator import ExperimentResultComparator


EXPERIMENTS = [
    {"name": "ModelA", "metrics": {"F1": 0.85, "Precision": 0.88, "latency_ms": 120}},
    {"name": "ModelB", "metrics": {"F1": 0.91, "Precision": 0.90, "latency_ms": 200}},
    {"name": "ModelC", "metrics": {"F1": 0.78, "Precision": 0.82, "latency_ms": 90}},
]


@pytest.fixture
def skill():
    return ExperimentResultComparator()


def test_ranking(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "primary_metric": "F1",
        "include_tradeoff": False,
        "output_format": "json",
    })
    assert result.success
    ranking = result.data["ranking"]
    assert ranking[0]["name"] == "ModelB"   # highest F1
    assert ranking[-1]["name"] == "ModelC"  # lowest F1


def test_best_per_metric(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "primary_metric": "F1",
        "include_tradeoff": False,
        "output_format": "json",
    })
    bpm = result.data["best_per_metric"]
    assert bpm["F1"]["best_model"] == "ModelB"
    # Default higher_is_better=True for all metrics, so "best" latency_ms = ModelB (highest value = 200)
    assert bpm["latency_ms"]["best_model"] == "ModelB"


def test_lower_is_better(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "primary_metric": "latency_ms",
        "higher_is_better": {"F1": True, "Precision": True, "latency_ms": False},
        "include_tradeoff": False,
        "output_format": "json",
    })
    bpm = result.data["best_per_metric"]
    assert bpm["latency_ms"]["best_model"] == "ModelC"


def test_latex_output(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "output_format": "latex",
        "include_tradeoff": False,
    })
    assert result.success
    latex = result.data["latex_table"]
    assert "\\begin{table}" in latex
    assert "\\textbf" in latex   # best value is bolded
    assert "ModelB" in latex


def test_markdown_output(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "output_format": "markdown",
        "include_tradeoff": False,
    })
    assert result.success
    md = result.data["markdown_table"]
    assert "| Model |" in md
    assert "**" in md  # best value bold


def test_conclusions_generated(skill):
    result = skill({
        "experiments": EXPERIMENTS,
        "include_tradeoff": False,
        "output_format": "json",
    })
    assert result.success
    assert len(result.data["conclusions"]) > 0


def test_tradeoff_analysis_mocked(skill):
    with patch.object(skill, "_tradeoff_analysis", return_value="Mocked analysis."):
        result = skill({
            "experiments": EXPERIMENTS,
            "include_tradeoff": True,
            "output_format": "json",
        })
    assert result.data["tradeoff_analysis"] == "Mocked analysis."


def test_empty_experiments(skill):
    result = skill({"experiments": []})
    assert result.success is False


def test_single_experiment(skill):
    result = skill({
        "experiments": [{"name": "OnlyModel", "metrics": {"F1": 0.90}}],
        "include_tradeoff": False,
    })
    assert result.success
    assert result.data["ranking"][0]["name"] == "OnlyModel"
