# Normality Testing Guide

Before deciding between parametric and non-parametric tests, verify whether your data satisfies the normality assumption.

## Choosing a Normality Test

| Sample size | Recommended test |
|-------------|-----------------|
| n ≤ 50 | Shapiro-Wilk (most powerful for small samples) |
| 50 < n ≤ 2000 | Shapiro-Wilk or Lilliefors (KS with estimated parameters) |
| n > 2000 | D'Agostino–Pearson K² (Shapiro-Wilk loses power for large n) |

**Always complement with a Q-Q plot** — significance tests can reject normality for trivially small deviations at large n.

## Python Code

```python
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

data = [...]  # your data

# Shapiro-Wilk test
stat, p = stats.shapiro(data)
print(f"Shapiro-Wilk: W={stat:.4f}, p={p:.4f}")
if p > 0.05:
    print("Data appears normally distributed (fail to reject H0)")
else:
    print("Data deviates from normality (reject H0)")

# Q-Q plot
fig, ax = plt.subplots()
stats.probplot(data, dist="norm", plot=ax)
ax.set_title("Q-Q Plot")
plt.tight_layout()
plt.savefig("qqplot.png")
print("Q-Q plot saved to qqplot.png")
```

## R Code

```r
data <- c(...)  # your data

# Shapiro-Wilk
shapiro.test(data)

# Q-Q plot
qqnorm(data)
qqline(data, col = "red")
```

## Interpreting the Q-Q Plot

- **Points follow the diagonal line closely** → data is approximately normal
- **S-shaped curve** → heavy tails (kurtosis) or light tails
- **Points curve away at one end** → skewness
- **A few points far off** → outliers (investigate before proceeding)

## Decision Rule

```
normality test p > 0.05  AND  Q-Q plot looks acceptable
    → Use parametric test (t-test, ANOVA, Pearson r)

Otherwise:
    → Use non-parametric alternative (Mann-Whitney U, Kruskal-Wallis, Spearman r)
    → Or apply transformation (log, sqrt, Box-Cox) and re-test
```

## Homogeneity of Variance (for group comparisons)

After confirming normality, check equal variances (required for standard t-test and ANOVA):

```python
# Levene's test (robust to non-normality)
from scipy.stats import levene
stat, p = levene(group1, group2)
print(f"Levene's test: F={stat:.4f}, p={p:.4f}")
# p < 0.05 → unequal variances → use Welch's t-test: ttest_ind(..., equal_var=False)
```
