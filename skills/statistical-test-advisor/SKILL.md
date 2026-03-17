---
name: statistical-test-advisor
description: Recommend the appropriate statistical test for a research design, provide assumption checklists, Python and R code, and optionally run the test on provided data. Use when a researcher needs to choose between t-test, ANOVA, Mann-Whitney, chi-square, correlation tests, etc. Especially useful for non-CS researchers (social science, medicine, psychology) who are less confident about statistics.
---

# Statistical Test Advisor

Recommends appropriate statistical tests based on research design using a decision tree, generates ready-to-run Python and R code, and optionally executes the test on actual data with a written interpretation.

## When to Use

- User needs to pick a statistical test for their study design
- User wants to know whether to use a parametric or non-parametric test
- User wants Python or R code for their analysis
- User has actual data and wants to run the test and get an interpretation

## Decision Tree Summary

Before running the script, use these questions to gather information from the user:

1. **What is your research question type?**
   - `group_comparison` — comparing means/distributions across groups
   - `correlation` — measuring linear/monotonic association between two variables
   - `association` — testing independence between categorical variables

2. **How many groups?** (2 groups vs. 3 or more)

3. **What type is the outcome variable?**
   - `continuous` — measured on a numeric scale (height, test score, reaction time)
   - `ordinal` — ordered categories (Likert scale, rating 1-5)
   - `categorical` — unordered categories (gender, disease type)
   - `binary` — only two categories (yes/no, pass/fail)

4. **Are the samples paired/matched?**
   - Paired: same participants at two time points, or matched case-control pairs
   - Independent: different participants in each group

5. **How large are your samples?** (sample sizes per group)

6. **Can normality be assumed?** (or: "Do you know if your data is normally distributed?")

## Step-by-Step Instructions

1. **Gather the design information** from the user using the questions above.

2. **Create input JSON** at `/tmp/stats_input.json`:

   ```json
   {
     "research_question_type": "group_comparison",
     "num_groups": 2,
     "variable_type": "continuous",
     "paired": false,
     "sample_size": [35, 32],
     "assume_normality": null,
     "alpha": 0.05,
     "context": "Comparing exam scores between control and treatment groups"
   }
   ```

   To also **run the test on actual data**, add:
   ```json
   "data": [[score1, score2, ...], [score1, score2, ...]]
   ```

3. **Run the advisor script**:

   ```bash
   python skills/statistical-test-advisor/run.py --input /tmp/stats_input.json
   ```

4. **Present the results** to the user:
   - Name and brief description of the primary recommended test
   - **Assumption checklist** — explain each assumption and how to verify it
   - **Python code** — ready to copy and run
   - **R code** — for users preferring R
   - If test was run: the statistic, p-value, significance decision, and interpretation

5. **If normality is uncertain** (`assume_normality: null`), suggest running Shapiro-Wilk first. See `docs/normality-testing.md`.

## Common Test Recommendations by Design

| Design | Recommended Test |
|--------|-----------------|
| 2 groups, continuous, independent, normal | Independent t-test |
| 2 groups, continuous, independent, non-normal or small n | Mann-Whitney U |
| 2 groups, continuous, paired | Paired t-test |
| 2 groups, continuous, paired, non-normal | Wilcoxon signed-rank |
| 3+ groups, continuous, independent, normal | One-way ANOVA |
| 3+ groups, continuous, independent, non-normal | Kruskal-Wallis H |
| 3+ conditions, same participants | Repeated-measures ANOVA |
| 2 categorical variables | Chi-square |
| 2 categorical variables, small sample | Fisher's exact test |
| Paired binary | McNemar's test |
| 2 continuous variables, linear | Pearson correlation |
| 2 continuous/ordinal variables, non-parametric | Spearman rank correlation |

For detailed guidance on normality testing and assumption verification, read `docs/normality-testing.md`.
