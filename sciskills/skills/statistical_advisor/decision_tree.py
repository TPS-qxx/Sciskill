"""
Decision tree for recommending statistical tests.
Pure logic — no LLM needed.

Reference: Field (2013) Discovering Statistics Using IBM SPSS;
           Zar (2010) Biostatistical Analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestRecommendation:
    test_name: str
    python_package: str
    python_function: str
    r_function: str
    description: str
    assumptions: list[str]
    when_violated: str
    effect_size_measure: str
    references: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ #
# Test catalog                                                         #
# ------------------------------------------------------------------ #

TESTS: dict[str, TestRecommendation] = {
    "independent_t": TestRecommendation(
        test_name="Independent Samples t-test",
        python_package="scipy.stats",
        python_function="ttest_ind(group1, group2)",
        r_function="t.test(x, y)",
        description="Compare means of two independent groups on a continuous variable.",
        assumptions=["Normality within each group", "Homogeneity of variance", "Independence"],
        when_violated="Use Mann-Whitney U test (non-parametric alternative).",
        effect_size_measure="Cohen's d",
    ),
    "paired_t": TestRecommendation(
        test_name="Paired Samples t-test",
        python_package="scipy.stats",
        python_function="ttest_rel(pre, post)",
        r_function="t.test(x, y, paired=TRUE)",
        description="Compare means of the same group measured at two time points.",
        assumptions=["Differences are normally distributed", "Independence of pairs"],
        when_violated="Use Wilcoxon signed-rank test.",
        effect_size_measure="Cohen's d (paired)",
    ),
    "one_way_anova": TestRecommendation(
        test_name="One-Way ANOVA",
        python_package="scipy.stats",
        python_function="f_oneway(group1, group2, group3)",
        r_function="aov(score ~ group, data=df)",
        description="Compare means across 3+ independent groups.",
        assumptions=["Normality within each group", "Homogeneity of variance", "Independence"],
        when_violated="Use Kruskal-Wallis H test.",
        effect_size_measure="Eta-squared (η²) or Omega-squared (ω²)",
    ),
    "repeated_anova": TestRecommendation(
        test_name="One-Way Repeated Measures ANOVA",
        python_package="pingouin",
        python_function="pg.rm_anova(data=df, dv='score', within='condition', subject='id')",
        r_function="aov(score ~ condition + Error(id/condition), data=df)",
        description="Compare means of the same participants across 3+ conditions.",
        assumptions=["Sphericity (Mauchly's test)", "Normality of residuals"],
        when_violated="Apply Greenhouse-Geisser correction or use Friedman test.",
        effect_size_measure="Partial eta-squared",
    ),
    "mann_whitney": TestRecommendation(
        test_name="Mann-Whitney U Test",
        python_package="scipy.stats",
        python_function="mannwhitneyu(group1, group2, alternative='two-sided')",
        r_function="wilcox.test(x, y)",
        description="Non-parametric comparison of two independent groups.",
        assumptions=["Independence", "Ordinal or continuous scale"],
        when_violated="No parametric assumption; robust alternative.",
        effect_size_measure="Rank-biserial correlation (r)",
    ),
    "wilcoxon": TestRecommendation(
        test_name="Wilcoxon Signed-Rank Test",
        python_package="scipy.stats",
        python_function="wilcoxon(pre, post)",
        r_function="wilcox.test(x, y, paired=TRUE)",
        description="Non-parametric alternative to paired t-test.",
        assumptions=["Paired/matched samples", "Symmetry of difference distribution"],
        when_violated="Use sign test (minimal assumptions).",
        effect_size_measure="Rank-biserial correlation (r)",
    ),
    "kruskal_wallis": TestRecommendation(
        test_name="Kruskal-Wallis H Test",
        python_package="scipy.stats",
        python_function="kruskal(group1, group2, group3)",
        r_function="kruskal.test(score ~ group, data=df)",
        description="Non-parametric alternative to one-way ANOVA.",
        assumptions=["Independence", "Ordinal or continuous scale"],
        when_violated="Already non-parametric. Post-hoc: Dunn's test.",
        effect_size_measure="Eta-squared (H-based)",
    ),
    "chi_square": TestRecommendation(
        test_name="Chi-Square Test of Independence",
        python_package="scipy.stats",
        python_function="chi2_contingency(contingency_table)",
        r_function="chisq.test(table(x, y))",
        description="Test association between two categorical variables.",
        assumptions=["Expected frequency ≥ 5 in each cell", "Independence"],
        when_violated="Use Fisher's exact test for small samples.",
        effect_size_measure="Cramér's V",
    ),
    "fisher_exact": TestRecommendation(
        test_name="Fisher's Exact Test",
        python_package="scipy.stats",
        python_function="fisher_exact(contingency_table_2x2)",
        r_function="fisher.test(table(x, y))",
        description="Exact test for association in 2×2 contingency tables (small samples).",
        assumptions=["Fixed marginals", "Independence"],
        when_violated="N/A — use for small expected frequencies.",
        effect_size_measure="Odds ratio",
    ),
    "pearson_r": TestRecommendation(
        test_name="Pearson Correlation",
        python_package="scipy.stats",
        python_function="pearsonr(x, y)",
        r_function="cor.test(x, y, method='pearson')",
        description="Linear association between two continuous variables.",
        assumptions=["Bivariate normality", "Linear relationship", "No outliers"],
        when_violated="Use Spearman's rank correlation.",
        effect_size_measure="r (r² = variance explained)",
    ),
    "spearman_r": TestRecommendation(
        test_name="Spearman Rank Correlation",
        python_package="scipy.stats",
        python_function="spearmanr(x, y)",
        r_function="cor.test(x, y, method='spearman')",
        description="Monotonic association between two ordinal or continuous variables.",
        assumptions=["Ordinal scale", "Monotonic relationship"],
        when_violated="Robust to non-normality and outliers.",
        effect_size_measure="ρ (rho)",
    ),
    "mcnemar": TestRecommendation(
        test_name="McNemar's Test",
        python_package="statsmodels.stats.contingency_tables",
        python_function="mcnemar(table, exact=True)",
        r_function="mcnemar.test(table)",
        description="Compare paired binary/categorical outcomes (before-after designs).",
        assumptions=["Paired binary data", "Mutually exclusive categories"],
        when_violated="N/A",
        effect_size_measure="Odds ratio",
    ),
}


# ------------------------------------------------------------------ #
# Decision tree                                                        #
# ------------------------------------------------------------------ #

def recommend_test(
    research_question_type: str,
    num_groups: int,
    variable_type: str,
    paired: bool,
    sample_size: list[int] | None = None,
    assume_normality: bool | None = None,
) -> list[TestRecommendation]:
    """
    Return a ranked list of recommended tests.

    Args:
        research_question_type: "group_comparison" | "correlation" | "association"
        num_groups: number of groups/conditions (1=one-sample, 2=two-group, 3+=multi)
        variable_type: "continuous" | "ordinal" | "categorical" | "binary"
        paired: whether samples are paired/matched
        sample_size: list of sample sizes per group
        assume_normality: if None, flag as "check required"
    """
    recs: list[TestRecommendation] = []
    rqt = research_question_type.lower()
    vt = variable_type.lower()

    # Small sample warning
    small_sample = sample_size and any(n < 30 for n in sample_size)

    # ---- Correlation / association ----
    if rqt in ("correlation", "relationship"):
        if vt in ("continuous",):
            if small_sample or assume_normality is False:
                recs.append(TESTS["spearman_r"])
                recs.append(TESTS["pearson_r"])
            else:
                recs.append(TESTS["pearson_r"])
                recs.append(TESTS["spearman_r"])
        elif vt in ("ordinal", "binary"):
            recs.append(TESTS["spearman_r"])

    elif rqt in ("association", "independence"):
        if vt in ("categorical", "binary"):
            if small_sample:
                recs.append(TESTS["fisher_exact"])
                recs.append(TESTS["chi_square"])
            else:
                recs.append(TESTS["chi_square"])
                recs.append(TESTS["fisher_exact"])
        if paired and vt == "binary":
            recs = [TESTS["mcnemar"]]

    # ---- Group comparison ----
    elif rqt in ("group_comparison", "difference", "comparison"):
        if num_groups == 2:
            if paired:
                if vt == "continuous":
                    if assume_normality is False or small_sample:
                        recs.append(TESTS["wilcoxon"])
                        recs.append(TESTS["paired_t"])
                    else:
                        recs.append(TESTS["paired_t"])
                        recs.append(TESTS["wilcoxon"])
                elif vt in ("ordinal",):
                    recs.append(TESTS["wilcoxon"])
                elif vt == "binary":
                    recs.append(TESTS["mcnemar"])
            else:
                if vt == "continuous":
                    if assume_normality is False or small_sample:
                        recs.append(TESTS["mann_whitney"])
                        recs.append(TESTS["independent_t"])
                    else:
                        recs.append(TESTS["independent_t"])
                        recs.append(TESTS["mann_whitney"])
                elif vt in ("ordinal",):
                    recs.append(TESTS["mann_whitney"])
                elif vt in ("categorical", "binary"):
                    recs.append(TESTS["chi_square"])

        elif num_groups >= 3:
            if paired:
                if vt == "continuous":
                    if assume_normality is False:
                        recs.append(TESTS["kruskal_wallis"])
                        recs.append(TESTS["repeated_anova"])
                    else:
                        recs.append(TESTS["repeated_anova"])
                        recs.append(TESTS["kruskal_wallis"])
                else:
                    recs.append(TESTS["kruskal_wallis"])
            else:
                if vt == "continuous":
                    if assume_normality is False or small_sample:
                        recs.append(TESTS["kruskal_wallis"])
                        recs.append(TESTS["one_way_anova"])
                    else:
                        recs.append(TESTS["one_way_anova"])
                        recs.append(TESTS["kruskal_wallis"])
                elif vt in ("ordinal",):
                    recs.append(TESTS["kruskal_wallis"])
                elif vt in ("categorical",):
                    recs.append(TESTS["chi_square"])

    # Fallback
    if not recs:
        recs = [TESTS["mann_whitney"], TESTS["kruskal_wallis"]]

    return recs
