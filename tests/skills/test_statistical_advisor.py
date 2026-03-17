"""Tests for StatisticalTestAdvisor — no LLM required for decision tree."""
import pytest
from unittest.mock import patch

from sciskills.skills.statistical_advisor import StatisticalTestAdvisor
from sciskills.skills.statistical_advisor.decision_tree import recommend_test


# ------------------------------------------------------------------ #
# Decision tree unit tests                                             #
# ------------------------------------------------------------------ #

def test_two_group_continuous_independent():
    recs = recommend_test("group_comparison", 2, "continuous", False)
    assert recs[0].test_name == "Independent Samples t-test"


def test_two_group_paired():
    recs = recommend_test("group_comparison", 2, "continuous", True)
    assert recs[0].test_name == "Paired Samples t-test"


def test_three_group_anova():
    recs = recommend_test("group_comparison", 3, "continuous", False)
    assert recs[0].test_name == "One-Way ANOVA"


def test_small_sample_nonparametric():
    recs = recommend_test("group_comparison", 2, "continuous", False, sample_size=[10, 8])
    assert "Mann-Whitney" in recs[0].test_name


def test_categorical_chi_square():
    recs = recommend_test("association", 2, "categorical", False)
    assert "Chi-Square" in recs[0].test_name


def test_correlation_continuous():
    recs = recommend_test("correlation", 2, "continuous", False)
    assert "Pearson" in recs[0].test_name


def test_correlation_ordinal():
    recs = recommend_test("correlation", 2, "ordinal", False)
    assert "Spearman" in recs[0].test_name


def test_non_normal_two_group():
    recs = recommend_test("group_comparison", 2, "continuous", False, assume_normality=False)
    assert "Mann-Whitney" in recs[0].test_name


# ------------------------------------------------------------------ #
# Skill integration tests                                              #
# ------------------------------------------------------------------ #

@pytest.fixture
def skill():
    return StatisticalTestAdvisor()


def test_basic_recommendation(skill):
    with patch.object(skill, "_generate_interpretation", return_value="mock interpretation"):
        result = skill({
            "research_question_type": "group_comparison",
            "num_groups": 2,
            "variable_type": "continuous",
            "paired": False,
        })
    assert result.success
    assert len(result.data["recommended_tests"]) >= 1
    assert result.data["primary_recommendation"]["test_name"]
    assert len(result.data["assumption_checklist"]) > 0


def test_code_generation(skill):
    with patch.object(skill, "_generate_interpretation", return_value="ok"):
        result = skill({
            "research_question_type": "group_comparison",
            "num_groups": 2,
            "variable_type": "continuous",
            "paired": False,
        })
    assert "scipy" in result.data["python_code"] or "ttest" in result.data["python_code"]
    assert "t.test" in result.data["r_code"] or "wilcox" in result.data["r_code"]


def test_with_actual_data(skill):
    import numpy as np
    rng = np.random.default_rng(42)
    g1 = rng.normal(10, 2, 30).tolist()
    g2 = rng.normal(12, 2, 30).tolist()

    with patch.object(skill, "_generate_interpretation", return_value="ok"):
        result = skill({
            "research_question_type": "group_comparison",
            "num_groups": 2,
            "variable_type": "continuous",
            "paired": False,
            "data": [g1, g2],
        })
    assert result.success
    assert "statistic" in result.data["test_results"]
    assert "p_value" in result.data["test_results"]
    assert "significant" in result.data["test_results"]


def test_three_group_with_data(skill):
    import numpy as np
    rng = np.random.default_rng(0)
    groups = [rng.normal(i * 2, 1, 20).tolist() for i in range(3)]

    with patch.object(skill, "_generate_interpretation", return_value="ok"):
        result = skill({
            "research_question_type": "group_comparison",
            "num_groups": 3,
            "variable_type": "continuous",
            "paired": False,
            "data": groups,
        })
    assert result.success
    assert result.data["test_results"].get("statistic") is not None
