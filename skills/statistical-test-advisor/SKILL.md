---
name: statistical-test-advisor
description: Two-phase statistical analysis assistant for researchers. Phase 1 (selector): recommend the appropriate statistical test for a given research design using a decision tree, with a full assumptions checklist and Python/R code. Phase 2 (runner): execute the test on provided data and generate an interpreted result paragraph. Use for group comparisons, correlation analysis, or association testing — especially for non-CS researchers (social science, medicine, psychology, education) who are less confident about choosing statistical methods. Do NOT use when the user already knows which test to run (go straight to runner), when the study design is incompletely specified, or when the data violates all available tests (consult a statistician instead).
---

# Statistical Test Advisor

A two-phase tool: first **selects** the right test using a rule-based decision tree (no LLM, deterministic), then optionally **runs** the test on actual data and generates an interpreted result with actionable language.

**This skill does not replace professional statistical consultation.** For high-stakes research (clinical trials, policy decisions), results should be reviewed by a qualified statistician.

---

## Phase 1 — Test Selector

### Input Schema (Selector)

```json
{
  "phase":                    "'select' (required for this phase)",
  "research_question_type":   "'group_comparison' | 'correlation' | 'association'",
  "num_groups":               "integer ≥ 2",
  "variable_type":            "'continuous' | 'ordinal' | 'categorical' | 'binary'",
  "paired":                   "boolean — true if same participants at multiple time points",
  "sample_size":              "[integer, ...] — one per group",
  "assume_normality":         "boolean | null — null means 'unknown, run normality test first'",
  "research_context":         "string | null — describe your study briefly"
}
```

**All fields except `research_context` are required for Phase 1.**

### Decision Tree Summary

```
research_question_type
├── group_comparison
│   ├── 2 groups, continuous, independent
│   │   ├── normal + large n → Student t-test
│   │   ├── normal + unequal variance → Welch t-test
│   │   └── non-normal OR n < 30 → Mann-Whitney U
│   ├── 2 groups, continuous, paired
│   │   ├── normal differences → Paired t-test
│   │   └── non-normal → Wilcoxon signed-rank
│   ├── 2 groups, binary, paired → McNemar's test
│   ├── 3+ groups, continuous, independent
│   │   ├── normal + equal var → One-way ANOVA
│   │   └── non-normal → Kruskal-Wallis H
│   ├── 3+ groups, continuous, repeated → Repeated measures ANOVA
│   └── categorical → Chi-square (n≥5 per cell) or Fisher exact
├── correlation
│   ├── continuous, bivariate normal → Pearson r
│   └── ordinal or non-normal → Spearman ρ
└── association
    ├── 2×2 table, small n → Fisher exact
    └── larger table → Chi-square
```

### Output Schema (Selector)

```json
{
  "phase": "select",
  "primary_recommendation": {
    "test_name":          "string",
    "python_package":     "string",
    "python_function":    "string",
    "r_function":         "string",
    "description":        "string",
    "effect_size_measure":"string",
    "why_chosen":         "string"
  },
  "alternatives": [
    {
      "test_name":   "string",
      "when_to_use": "string"
    }
  ],
  "assumptions_checklist": [
    {
      "assumption":    "string",
      "how_to_verify": "string",
      "status":        "'user_asserted' | 'not_verified' | 'violated' | 'checked_by_data'"
    }
  ],
  "warnings": ["string — e.g. 'small sample size (n<30), consider non-parametric'"],
  "python_code": "string — ready-to-run scipy/pingouin code",
  "r_code":      "string — equivalent R code",
  "next_step":   "string — guidance: 'run normality check first' OR 'proceed to phase=run'"
}
```

---

## Phase 2 — Test Runner

### Input Schema (Runner)

```json
{
  "phase":      "'run' (required for this phase)",
  "test_name":  "string — from Phase 1 output or user-specified",
  "data":       [[0.0, ...], [0.0, ...]] ,
  "alpha":      "number — significance level, default 0.05",
  "context":    "string | null — study description for interpretation"
}
```

**`data` is required: a list of groups, each group is a list of numbers.**

### Output Schema (Runner)

```json
{
  "phase": "run",
  "test_name":  "string",
  "statistic":  0.0,
  "p_value":    0.0,
  "significant": true,
  "alpha":      0.05,
  "effect_size": {
    "name":  "string",
    "value": 0.0,
    "interpretation": "negligible | small | medium | large"
  },
  "confidence_interval": [0.0, 0.0],
  "interpretation": "string — LLM-generated plain-language paragraph",
  "report_sentence": "string — ready to paste into paper Methods/Results section",
  "warnings": ["string"]
}
```

---

## When to Use

- Researcher is unsure which test to choose → use `phase=select`
- Researcher has decided on a test and has data → use `phase=run` directly
- Non-CS researcher needs guidance on normality, variance homogeneity, or sample size adequacy
- User wants ready-to-run Python/R code for their analysis

## When NOT to Use

- **Design is incompletely specified**: "I have some data, what test should I use?" is not enough — you must gather `num_groups`, `variable_type`, `paired`, and `sample_size` first
- **Multiple comparisons**: if the user has more than one hypothesis test (e.g. ANOVA followed by post-hoc), this skill handles only a single test at a time; explicitly state that multiple-comparison correction (Bonferroni, FDR) is required
- **All assumptions violated**: if the data is too small for any parametric test AND non-parametric alternatives don't apply, state this clearly and advise consulting a statistician
- **High-stakes clinical or regulatory context**: always add a disclaimer that professional statistical review is required

## Step-by-Step Instructions

### Phase 1: Select

1. **Gather design information** from the user:
   - What are you comparing? (groups, correlation, or association?)
   - How many groups?
   - What type is the outcome variable?
   - Is the design paired or independent?
   - What are the sample sizes?
   - Is normality known or assumed?

2. **Create input JSON** at `/tmp/stats_select.json`.

3. **Run**:
   ```bash
   python skills/statistical-test-advisor/run.py --input /tmp/stats_select.json
   ```

4. **Present**: test name + `why_chosen`, full `assumptions_checklist`, Python and R code.

5. **Check `next_step`**:
   - If `"run normality check first"` → show normality testing code from `docs/normality-testing.md` before proceeding
   - If `"proceed to phase=run"` → ask user if they have data

### Phase 2: Run

1. **Ask the user to provide their data** as numeric arrays.

2. **Create input JSON** at `/tmp/stats_run.json`:
   ```json
   {
     "phase": "run",
     "test_name": "independent_t",
     "data": [[85, 92, 78, ...], [71, 88, 65, ...]],
     "alpha": 0.05,
     "context": "Comparing exam scores between control and treatment groups"
   }
   ```

3. **Run**:
   ```bash
   python skills/statistical-test-advisor/run.py --input /tmp/stats_run.json
   ```

4. **Present**:
   - Test statistic and p-value
   - Significance decision at stated α
   - Effect size with Cohen's guidelines interpretation
   - `report_sentence` verbatim (paste-ready for paper)

5. **Always include `warnings`** if present — common ones: small n, borderline p-value, assumption not verified.

## Known Limitations

- Normality assumption defaults to `not_verified` unless the user explicitly asserts it or provides data for the normality check
- Effect size computation is available for t-tests (Cohen's d), Mann-Whitney (rank-biserial r), ANOVA (η²), and correlations (r); not yet available for chi-square or Fisher exact
- The `interpretation` field is LLM-generated and should be reviewed before inclusion in a manuscript
- Does not handle nested, multilevel, or longitudinal designs

For normality testing guidance, see `docs/normality-testing.md`.
