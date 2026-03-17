---
name: reproducibility-checker
description: Check a machine learning research GitHub repository for common reproducibility issues. Returns a score from 0-100 and a detailed checklist. Use when the user wants to assess or improve the reproducibility of their own code repository before paper submission, or when reviewing someone else's code. Can analyze a GitHub URL (auto-clones) or a local directory.
---

# Reproducibility Checker

Performs static analysis on a code repository to detect common reproducibility problems. Inspired by the NeurIPS Reproducibility Checklist. Returns a 0-100 score and actionable suggestions.

## When to Use

- Researcher is preparing to release code alongside a paper submission
- Reviewer wants to quickly assess reproducibility of a public repo
- User wants guidance on what reproducibility standards to meet
- CI/CD integration for ongoing reproducibility tracking

## Step-by-Step Instructions

1. **Get the repository location** from the user:
   - A GitHub URL: `https://github.com/owner/repo`
   - A local directory path: `/path/to/my-project`

2. **Run the checker**:

   ```bash
   # Analyze a GitHub repo (auto-clones, then deletes the clone):
   python skills/reproducibility-checker/run.py --repo https://github.com/owner/repo

   # Analyze a local directory:
   python skills/reproducibility-checker/run.py --local /path/to/project

   # Keep the clone after analysis:
   python skills/reproducibility-checker/run.py --repo https://github.com/owner/repo --keep
   ```

3. **Interpret the score**:

   | Score | Level | Meaning |
   |-------|-------|---------|
   | 85–100 | Excellent | Ready for paper submission |
   | 70–84 | Good | Minor improvements recommended |
   | 50–69 | Moderate | Several issues to address |
   | 0–49 | Poor | Significant reproducibility concerns |

4. **Report findings** to the user:
   - Show the score prominently
   - List all **failed checks** grouped by severity (error → warning → info)
   - For each failed check, give the specific suggestion and, if available, the offending file(s)
   - Acknowledge passing checks briefly

5. **Prioritize fixes** by severity:
   - `error`: Fix before submission (missing requirements.txt, etc.)
   - `warning`: Fix if possible (hardcoded paths, missing seed)
   - `info`: Nice-to-have (Docker support, license file)

## Checks Performed

### Error-severity (−15 pts each if failed)
- **Dependency specification file exists** — requirements.txt, pyproject.toml, environment.yml, Pipfile, etc.
- **README with setup instructions** — must mention installation and usage/training/evaluation

### Warning-severity (−7 pts each if failed)
- **Random seed is fixed** — detects `torch.manual_seed()`, `np.random.seed()`, `random.seed()`, `set_seed()`
- **Training scripts set random seeds (AST check)** — scripts named `train.py`, `main.py`, etc. that import random libraries should also call seed functions
- **No hardcoded absolute paths** — detects `/home/user/...`, `/Users/...`, `C:\...` in Python files
- **Data download/preparation script exists** — `download_data.sh`, `Makefile` with wget/curl, etc.

### Info-severity (−3 pts each if failed)
- **Model checkpoint or download link available** — `.ckpt`, `.pth`, `.bin` files or mention in README
- **Experiment configuration files exist** — YAML/JSON config files for hyperparameters
- **License file exists** — LICENSE or LICENCE file
- **Docker / container support** — Dockerfile or docker-compose.yml

## Notes

- For GitHub repos, requires `git` to be installed. Uses a shallow clone (`--depth 1`) for speed.
- The clone is automatically deleted after analysis unless `--keep` is specified.
- AST-based seed checking only analyzes Python files named `train*.py`, `main*.py`, `run*.py`, or `finetune*.py`.
- Score is additive: 100 minus penalty points for each failed check. Minimum score is 0.

For detailed explanations of each check, see `docs/checks-reference.md`.
