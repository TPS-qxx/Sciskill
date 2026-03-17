"""
Skill 4: Statistical Test Advisor

Inputs:
  - research_question_type: "group_comparison" | "correlation" | "association"
  - num_groups: int
  - variable_type: "continuous" | "ordinal" | "categorical" | "binary"
  - paired: bool
  - sample_size: list[int] (optional)
  - assume_normality: bool | null (optional)
  - data: list of lists (optional — actual data for running the test)
  - alpha: float (significance level, default 0.05)

Output:
  {
    "recommended_tests": [...],
    "primary_recommendation": {...},
    "assumption_checklist": [...],
    "python_code": "...",
    "r_code": "...",
    "test_results": {...} (if data provided),
    "interpretation": "..." (LLM-generated)
  }
"""
from __future__ import annotations

from typing import Any

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.skills.statistical_advisor.decision_tree import (
    TestRecommendation,
    recommend_test,
)
from sciskills.utils.llm_client import get_default_client


_CODE_TEMPLATE_PYTHON = '''import numpy as np
from scipy import stats
{extra_imports}

# --- Your data ---
# Replace with your actual data arrays
{data_setup}

# --- {test_name} ---
result = {python_function}
print(f"Test statistic: {{result.statistic:.4f}}")
print(f"p-value: {{result.pvalue:.4f}}")
alpha = {alpha}
if result.pvalue < alpha:
    print(f"Reject H0: significant difference (p < {{alpha}})")
else:
    print(f"Fail to reject H0: no significant difference (p >= {{alpha}})")

# --- Effect size ---
# {effect_size_measure}
# Compute effect size here as appropriate for your data.
'''

_CODE_TEMPLATE_R = '''# --- {test_name} ---
# Replace with your actual data
{r_data_setup}

result <- {r_function}
print(result)

alpha <- {alpha}
if (result$p.value < alpha) {{
  cat("Reject H0: significant difference\\n")
}} else {{
  cat("Fail to reject H0\\n")
}}
'''


def _build_assumption_checklist(rec: TestRecommendation) -> list[dict]:
    return [
        {"assumption": a, "check_method": _assumption_check_hint(a)}
        for a in rec.assumptions
    ]


def _assumption_check_hint(assumption: str) -> str:
    hints = {
        "normality": "Shapiro-Wilk test (n<50) or Kolmogorov-Smirnov; Q-Q plot",
        "homogeneity of variance": "Levene's test: scipy.stats.levene(*groups)",
        "independence": "Study design check — no repeated measures or clustering",
        "sphericity": "Mauchly's test (built into pingouin rm_anova)",
        "bivariate normality": "Check scatter plot and individual distributions",
        "linear relationship": "Scatter plot; residual plot after regression",
    }
    low = assumption.lower()
    for key, hint in hints.items():
        if key in low:
            return hint
    return "Review study design and data collection procedure."


@registry.register
class StatisticalTestAdvisor(BaseSkill):
    name = "statistical_test_advisor"
    description = (
        "Recommend appropriate statistical tests based on research design. "
        "Provides assumption checklists, Python/R code snippets, "
        "and optionally runs the test on provided data with LLM-generated interpretation."
    )
    input_schema = {
        "type": "object",
        "required": ["research_question_type", "num_groups", "variable_type", "paired"],
        "properties": {
            "research_question_type": {
                "type": "string",
                "enum": ["group_comparison", "correlation", "association"],
                "description": "Type of research question.",
            },
            "num_groups": {
                "type": "integer",
                "minimum": 1,
                "description": "Number of groups or conditions (2 for two-group, 3+ for multi-group).",
            },
            "variable_type": {
                "type": "string",
                "enum": ["continuous", "ordinal", "categorical", "binary"],
                "description": "Measurement level of the dependent/outcome variable.",
            },
            "paired": {
                "type": "boolean",
                "description": "Whether samples are paired or matched (repeated measures).",
            },
            "sample_size": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Sample sizes per group, e.g. [30, 28].",
            },
            "assume_normality": {
                "type": ["boolean", "null"],
                "description": "Whether normality can be assumed. null means 'run normality tests first'.",
            },
            "data": {
                "type": "array",
                "description": "Actual data: list of groups, each group is a list of numbers. E.g. [[1,2,3],[4,5,6]]",
                "items": {"type": "array", "items": {"type": "number"}},
            },
            "alpha": {
                "type": "number",
                "default": 0.05,
                "description": "Significance level (default: 0.05).",
            },
            "context": {
                "type": "string",
                "description": "Optional: describe your research context for a more tailored interpretation.",
            },
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "recommended_tests": {"type": "array"},
            "primary_recommendation": {"type": "object"},
            "assumption_checklist": {"type": "array"},
            "python_code": {"type": "string"},
            "r_code": {"type": "string"},
            "test_results": {"type": "object"},
            "interpretation": {"type": "string"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        rqt = params["research_question_type"]
        num_groups = params["num_groups"]
        vt = params["variable_type"]
        paired = params["paired"]
        sample_size = params.get("sample_size")
        assume_normality = params.get("assume_normality")
        data = params.get("data")
        alpha = params.get("alpha", 0.05)
        context = params.get("context", "")

        # 1. Get recommendations
        recommendations = recommend_test(
            research_question_type=rqt,
            num_groups=num_groups,
            variable_type=vt,
            paired=paired,
            sample_size=sample_size,
            assume_normality=assume_normality,
        )

        if not recommendations:
            return SkillResult.fail(errors=["Could not determine a suitable test for the given parameters."])

        primary = recommendations[0]

        # 2. Assumption checklist
        checklist = _build_assumption_checklist(primary)

        # 3. Code generation
        python_code = self._generate_python_code(primary, data, alpha, num_groups)
        r_code = self._generate_r_code(primary, data, alpha, num_groups)

        # 4. Optionally run test
        test_results = {}
        if data:
            test_results = self._run_test(primary, data, alpha)

        # 5. LLM interpretation
        interpretation = self._generate_interpretation(
            primary, test_results, alpha, context, rqt, num_groups, vt, paired
        )

        return SkillResult.ok(
            data={
                "recommended_tests": [
                    {
                        "test_name": r.test_name,
                        "description": r.description,
                        "python_function": r.python_function,
                        "r_function": r.r_function,
                        "assumptions": r.assumptions,
                        "when_violated": r.when_violated,
                        "effect_size_measure": r.effect_size_measure,
                    }
                    for r in recommendations
                ],
                "primary_recommendation": {
                    "test_name": primary.test_name,
                    "description": primary.description,
                    "assumptions": primary.assumptions,
                    "effect_size_measure": primary.effect_size_measure,
                },
                "assumption_checklist": checklist,
                "python_code": python_code,
                "r_code": r_code,
                "test_results": test_results,
                "interpretation": interpretation,
            }
        )

    # ------------------------------------------------------------------ #

    def _generate_python_code(
        self, rec: TestRecommendation, data: list | None, alpha: float, num_groups: int
    ) -> str:
        extra_imports = ""
        if rec.python_package == "pingouin":
            extra_imports = "import pingouin as pg\nimport pandas as pd"

        if data:
            groups = [f"group{i+1} = {g}" for i, g in enumerate(data)]
            data_setup = "\n".join(groups)
        else:
            groups = [f"group{i+1} = [...]  # your data here" for i in range(num_groups)]
            data_setup = "\n".join(groups)

        fn = rec.python_function
        # Replace generic variable names in function template
        for i in range(num_groups, 0, -1):
            fn = fn.replace(f"group{i}", f"group{i}")

        return _CODE_TEMPLATE_PYTHON.format(
            test_name=rec.test_name,
            extra_imports=extra_imports,
            data_setup=data_setup,
            python_function=fn,
            effect_size_measure=rec.effect_size_measure,
            alpha=alpha,
        )

    def _generate_r_code(
        self, rec: TestRecommendation, data: list | None, alpha: float, num_groups: int
    ) -> str:
        if data:
            r_groups = [
                f"group{i+1} <- c({', '.join(str(v) for v in g)})"
                for i, g in enumerate(data)
            ]
            r_data_setup = "\n".join(r_groups)
        else:
            r_groups = [f"group{i+1} <- c(...)  # your data" for i in range(num_groups)]
            r_data_setup = "\n".join(r_groups)

        return _CODE_TEMPLATE_R.format(
            test_name=rec.test_name,
            r_data_setup=r_data_setup,
            r_function=rec.r_function,
            alpha=alpha,
        )

    def _run_test(self, rec: TestRecommendation, data: list[list], alpha: float) -> dict:
        """Attempt to run the statistical test using scipy/pingouin."""
        try:
            from scipy import stats as scipy_stats

            fn_name = rec.python_function.split("(")[0].strip()

            if fn_name == "ttest_ind":
                stat, p = scipy_stats.ttest_ind(*data[:2])
            elif fn_name == "ttest_rel":
                stat, p = scipy_stats.ttest_rel(*data[:2])
            elif fn_name == "f_oneway":
                stat, p = scipy_stats.f_oneway(*data)
            elif fn_name == "mannwhitneyu":
                stat, p = scipy_stats.mannwhitneyu(*data[:2], alternative="two-sided")
            elif fn_name == "wilcoxon":
                stat, p = scipy_stats.wilcoxon(*data[:2])
            elif fn_name == "kruskal":
                stat, p = scipy_stats.kruskal(*data)
            elif fn_name == "chi2_contingency":
                stat, p, dof, expected = scipy_stats.chi2_contingency(data)
                return {
                    "statistic": round(float(stat), 4),
                    "p_value": round(float(p), 4),
                    "dof": int(dof),
                    "significant": bool(p < alpha),
                    "alpha": alpha,
                }
            elif fn_name == "pearsonr":
                stat, p = scipy_stats.pearsonr(*data[:2])
            elif fn_name == "spearmanr":
                stat, p = scipy_stats.spearmanr(*data[:2])
            else:
                return {"error": f"Auto-run not supported for: {fn_name}"}

            return {
                "statistic": round(float(stat), 4),
                "p_value": round(float(p), 4),
                "significant": bool(p < alpha),
                "alpha": alpha,
            }
        except Exception as e:
            return {"error": str(e)}

    def _generate_interpretation(
        self,
        rec: TestRecommendation,
        test_results: dict,
        alpha: float,
        context: str,
        rqt: str,
        num_groups: int,
        vt: str,
        paired: bool,
    ) -> str:
        """Generate a natural language interpretation using LLM."""
        results_str = ""
        if test_results and "error" not in test_results:
            sig = "significant" if test_results.get("significant") else "not significant"
            results_str = (
                f"Test results: statistic={test_results.get('statistic')}, "
                f"p={test_results.get('p_value')}, {sig} at α={alpha}."
            )

        prompt = f"""You are a statistical methods expert helping a graduate researcher.

Research design:
- Question type: {rqt}
- Groups: {num_groups}, Variable type: {vt}, Paired: {paired}
- Recommended test: {rec.test_name}
- Effect size to report: {rec.effect_size_measure}
{f'- Context: {context}' if context else ''}
{results_str}

Write a brief (3-5 sentences) guidance paragraph covering:
1. Why this test is appropriate
2. What assumptions to verify before running it
3. How to report the results in a paper
{f'4. Interpretation of the specific results above' if results_str else ''}

Use clear, jargon-minimal language appropriate for a non-statistician researcher."""

        try:
            llm = get_default_client()
            return llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
            )
        except Exception as e:
            return (
                f"Recommended: {rec.test_name}. "
                f"Assumptions: {', '.join(rec.assumptions)}. "
                f"Effect size: {rec.effect_size_measure}."
            )
