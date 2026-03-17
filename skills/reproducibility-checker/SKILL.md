---
name: reproducibility-checker
description: Static-analysis reproducibility audit for a machine learning code repository. Returns two separate scores — runnability_score (can someone run the code at all?) and reproducibility_score (can someone reproduce the paper's numbers?) — plus a per-dimension checklist with transparent point weights and executable fix suggestions. Use when preparing code for paper submission, reviewing a public repo, or auditing your own project. Do NOT use for non-ML codebases (the rubric is ML-specific), for measuring result correctness (this is code-structure analysis only), or when no code repository is available.
---

# Reproducibility Checker

Rule-based static analysis of a code repository against the ML reproducibility rubric. **No LLM required — fully deterministic.** Returns two independently scored dimensions, a per-check breakdown showing exactly how each point was earned or lost, and copy-paste fix suggestions.

---

## Input Schema

```json
{
  "repo_url":    "string — GitHub/GitLab HTTPS URL (mutually exclusive with local_path)",
  "local_path":  "string — absolute path to local directory (mutually exclusive with repo_url)",
  "keep_clone":  "boolean — default false: delete clone after analysis",
  "checks":      ["string — subset of check IDs to run; default: run all"],
  "strict_mode": "boolean — default false: treat warnings as errors in score calculation"
}
```

**Exactly one of `repo_url` or `local_path` is required.**

---

## Output Schema

```json
{
  "runnability_score":      0,
  "reproducibility_score":  0,
  "overall_score":          0,
  "grade":                  "A | B | C | D | F",
  "checks": [
    {
      "check_id":      "string",
      "dimension":     "runnability | reproducibility",
      "severity":      "error | warning | info",
      "passed":        true,
      "points_possible": 0,
      "points_earned":   0,
      "description":   "string — what was checked",
      "finding":       "string | null — specific finding (e.g. offending file/line)",
      "fix_suggestion":"string | null — copy-paste ready fix instruction",
      "evidence":      ["string — file paths or code snippets that informed this check"]
    }
  ],
  "dimension_breakdown": {
    "runnability": {
      "score":    0,
      "max":      0,
      "pct":      0.0,
      "checks_passed": 0,
      "checks_failed": 0
    },
    "reproducibility": {
      "score":    0,
      "max":      0,
      "pct":      0.0,
      "checks_passed": 0,
      "checks_failed": 0
    }
  },
  "warnings": ["string — e.g. 'Could not parse Python AST in train.py: SyntaxError'"]
}
```

---

## Scoring Rubric

### Runnability dimension (max 50 pts)

Measures whether a new user can install and run the code without contacting the authors.

| Check ID | Description | Points | Severity |
|----------|-------------|--------|----------|
| `RUN-01` | Dependency specification exists (`requirements.txt`, `pyproject.toml`, `environment.yml`, `Pipfile`, `setup.py`) | 15 | error |
| `RUN-02` | README contains installation instructions (keyword: `install`, `pip`, `conda`) | 10 | error |
| `RUN-03` | README contains usage/training/evaluation instructions (keyword: `python`, `run`, `train`, `evaluate`) | 10 | error |
| `RUN-04` | Entry-point script exists (`train.py`, `main.py`, `run.py`, `finetune.py`, or Makefile) | 8 | warning |
| `RUN-05` | No hardcoded absolute paths in Python files (`/home/`, `/Users/`, `C:\`) | 7 | warning |

### Reproducibility dimension (max 50 pts)

Measures whether the paper's reported results can be independently re-obtained.

| Check ID | Description | Points | Severity |
|----------|-------------|--------|----------|
| `REP-01` | Random seed is fixed in entry-point scripts (`torch.manual_seed`, `np.random.seed`, `random.seed`, `set_seed`, `pl.seed_everything`) | 12 | warning |
| `REP-02` | Hyperparameter configuration file exists (`.yaml`, `.yml`, `.json` config under `configs/`, `config/`, or `hparams.*`) | 10 | warning |
| `REP-03` | Data download or preparation script exists (`download_data.sh`, `prepare_data.py`, Makefile with wget/curl, DVC `.dvc` files) | 10 | warning |
| `REP-04` | Pretrained checkpoint or model download link available (`.ckpt`, `.pth`, `.pt`, `.bin`, `model.safetensors`, or `wget`/`gdown`/`huggingface_hub` call in README) | 8 | info |
| `REP-05` | Experiment logging integration present (`wandb`, `mlflow`, `tensorboard`, `neptune`, `comet`) | 5 | info |
| `REP-06` | License file present (`LICENSE`, `LICENCE`, `LICENSE.txt`) | 3 | info |
| `REP-07` | Container/environment spec exists (`Dockerfile`, `docker-compose.yml`, `.devcontainer/`, `nix` flake) | 2 | info |

### Score → Grade mapping

| Overall score | Grade | Meaning |
|---------------|-------|---------|
| 90–100 | A | Submission-ready |
| 75–89 | B | Minor issues — fix before submission |
| 55–74 | C | Several gaps — address errors and warnings |
| 35–54 | D | Significant reproducibility concerns |
| 0–34 | F | Not reproducible without author assistance |

**`overall_score` = `runnability_score` + `reproducibility_score` (each out of 50).**

---

## When to Use

- Preparing code release alongside a paper submission (especially NeurIPS, ICML, ICLR which have reproducibility checklists)
- Self-auditing a repository before making it public
- Quick reproducibility assessment of someone else's public repo
- CI/CD gate: block merges that drop reproducibility below a threshold

## When NOT to Use

- **Non-ML codebases**: the rubric is calibrated for ML experiments (seeds, checkpoints, training scripts); it will produce misleading scores for web apps, data pipelines, etc.
- **Correctness verification**: this skill checks code structure, not whether the model actually produces the numbers in the paper — for that, you must run the code
- **No code repository available**: if only a PDF exists with no code link, this skill cannot run
- **Proprietary/private data-dependent repos**: `REP-03` will likely fail even if data preparation is well-documented; add a note when presenting results

---

## Step-by-Step Instructions

1. **Get the repository location** from the user (GitHub URL or local path).

2. **Run the checker**:
   ```bash
   # GitHub repository (auto-clones, deletes after):
   python skills/reproducibility-checker/run.py --repo https://github.com/owner/repo

   # Local directory:
   python skills/reproducibility-checker/run.py --local /path/to/project

   # Keep clone for inspection:
   python skills/reproducibility-checker/run.py --repo https://github.com/owner/repo --keep

   # Run only runnability checks (skip REP-*):
   python skills/reproducibility-checker/run.py --local /path/to/project \
     --checks RUN-01 RUN-02 RUN-03 RUN-04 RUN-05
   ```

3. **Present results** in this order:
   a. **Scores**: `runnability_score/50` and `reproducibility_score/50`, overall grade
   b. **Failed error-severity checks** first (these are blockers)
   c. **Failed warning-severity checks** with `fix_suggestion` for each
   d. **Passed checks** (brief acknowledgment)
   e. **`warnings`** from the analysis process (parser failures, etc.)

4. **For each failed check**, show:
   - Check ID and description
   - `finding` (specific file/line if available)
   - `fix_suggestion` verbatim (ready to act on)

5. **Prioritize remediation order**:
   - Fix `error` checks first (highest point value, most impactful)
   - Then `warning` checks in order of `points_possible` descending
   - `info` checks are optional improvements

6. **After user fixes issues**, offer to re-run to confirm improvement.

---

## Implementation Notes

- GitHub clone uses `--depth 1` (shallow) for speed; requires `git` to be installed
- AST-based seed check (`REP-01`) only parses files matching: `train*.py`, `main*.py`, `run*.py`, `finetune*.py`, `pretrain*.py`
- Hardcoded path check (`RUN-05`) scans all `.py` files; excludes `.git/`, `__pycache__/`, `node_modules/`
- Clone is auto-deleted unless `keep_clone=true`; if clone fails (private repo, no git), analysis aborts with an error

## Known Limitations

- AST parsing fails on Python files with syntax errors — these files are skipped and logged in `warnings`
- Cannot detect whether seed-setting calls are actually reached during execution (only checks for their presence)
- `REP-04` (checkpoint availability) may have false negatives for repos that use custom model hosting
- Does not check that hyperparameter config values match the paper — only that a config file exists

For detailed check implementation notes, see `docs/checks-reference.md`.
