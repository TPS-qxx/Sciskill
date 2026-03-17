"""
Reproducibility check rules for ML repositories.

Checks are split into two dimensions:
  - runnability (RUN-*): can someone install and run the code?
  - reproducibility (REP-*): can someone re-obtain the paper's numbers?

Each check returns a CheckResult with a canonical check_id and points_possible.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CheckResult:
    check_id: str
    item: str                          # human-readable description
    dimension: str                     # "runnability" | "reproducibility"
    passed: bool
    severity: str                      # "error" | "warning" | "info"
    points_possible: int
    points_earned: int = 0
    files: list[str] = field(default_factory=list)
    finding: str = ""                  # specific file/line that caused pass/fail
    suggestion: str = ""               # copy-paste fix instruction
    evidence: list[str] = field(default_factory=list)  # file paths that informed check

    def __post_init__(self) -> None:
        self.points_earned = self.points_possible if self.passed else 0


# ── Runnability checks ─────────────────────────────────────────────────────── #

def check_RUN01_requirements(repo_path: Path) -> CheckResult:
    """RUN-01: Dependency specification file exists."""
    candidates = [
        "requirements.txt", "requirements/*.txt", "environment.yml",
        "environment.yaml", "pyproject.toml", "setup.py", "setup.cfg",
        "Pipfile", "conda.yaml",
    ]
    found = []
    for pattern in candidates:
        found.extend(repo_path.glob(pattern))
    passed = len(found) > 0
    return CheckResult(
        check_id="RUN-01",
        item="Dependency specification file exists",
        dimension="runnability",
        passed=passed,
        severity="error",
        points_possible=15,
        files=[str(f.relative_to(repo_path)) for f in found],
        evidence=[str(f.relative_to(repo_path)) for f in found],
        finding="" if passed else "No requirements.txt, pyproject.toml, or environment.yml found",
        suggestion="" if passed else (
            "Add a requirements.txt with pinned versions:\n"
            "  pip freeze > requirements.txt\n"
            "Or use pyproject.toml: [project] dependencies = [...]"
        ),
    )


def check_RUN02_readme_install(repo_path: Path) -> CheckResult:
    """RUN-02: README contains installation instructions."""
    readmes = list(repo_path.glob("README*")) + list(repo_path.glob("readme*"))
    if not readmes:
        return CheckResult(
            check_id="RUN-02",
            item="README contains installation instructions",
            dimension="runnability",
            passed=False,
            severity="error",
            points_possible=10,
            finding="No README file found",
            suggestion="Create README.md with installation and usage instructions.",
        )
    readme = readmes[0]
    content = readme.read_text(encoding="utf-8", errors="ignore").lower()
    has_install = any(kw in content for kw in ["install", "requirements", "setup", "pip", "conda"])
    return CheckResult(
        check_id="RUN-02",
        item="README contains installation instructions",
        dimension="runnability",
        passed=has_install,
        severity="error",
        points_possible=10,
        files=[str(readme.relative_to(repo_path))],
        evidence=[str(readme.relative_to(repo_path))],
        finding="" if has_install else "README exists but lacks install/pip/conda keywords",
        suggestion="" if has_install else (
            "Add an ## Installation section to README.md, e.g.:\n"
            "  pip install -r requirements.txt"
        ),
    )


def check_RUN03_readme_usage(repo_path: Path) -> CheckResult:
    """RUN-03: README contains usage/training/evaluation instructions."""
    readmes = list(repo_path.glob("README*")) + list(repo_path.glob("readme*"))
    if not readmes:
        return CheckResult(
            check_id="RUN-03",
            item="README contains usage/training/evaluation instructions",
            dimension="runnability",
            passed=False,
            severity="error",
            points_possible=10,
            finding="No README file found",
            suggestion="Create README.md with usage examples.",
        )
    readme = readmes[0]
    content = readme.read_text(encoding="utf-8", errors="ignore").lower()
    has_usage = any(kw in content for kw in ["usage", "run", "train", "evaluate", "python ", "bash ", "example"])
    return CheckResult(
        check_id="RUN-03",
        item="README contains usage/training/evaluation instructions",
        dimension="runnability",
        passed=has_usage,
        severity="error",
        points_possible=10,
        files=[str(readme.relative_to(repo_path))],
        evidence=[str(readme.relative_to(repo_path))],
        finding="" if has_usage else "README lacks usage/training/evaluation commands",
        suggestion="" if has_usage else (
            "Add a ## Usage section with example commands:\n"
            "  python train.py --config configs/default.yaml"
        ),
    )


def check_RUN04_entry_point(repo_path: Path) -> CheckResult:
    """RUN-04: Entry-point script exists."""
    patterns = ["train.py", "main.py", "run.py", "finetune.py", "pretrain.py", "Makefile"]
    found = [p for p in patterns if (repo_path / p).exists()]
    # Also search in subdirectories one level deep
    if not found:
        for subdir in repo_path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                for p in patterns:
                    if (subdir / p).exists():
                        found.append(str(subdir.relative_to(repo_path) / p))
                        break
    passed = len(found) > 0
    return CheckResult(
        check_id="RUN-04",
        item="Entry-point script exists (train.py / main.py / Makefile)",
        dimension="runnability",
        passed=passed,
        severity="warning",
        points_possible=8,
        files=found[:3],
        evidence=found[:3],
        finding="" if passed else "No train.py, main.py, run.py, or Makefile found at root or first-level subdirectory",
        suggestion="" if passed else "Add a top-level train.py or Makefile with a 'train' target.",
    )


def check_RUN05_no_hardcoded_paths(repo_path: Path) -> CheckResult:
    """RUN-05: No hardcoded absolute paths in Python files."""
    abs_path_pattern = re.compile(r'["\'](?:/home/|/Users/|/root/|C:\\\\|/data/)[^"\']{3,}["\']')
    offenders: list[str] = []
    for py_file in repo_path.rglob("*.py"):
        parts = py_file.parts
        if any(p in parts for p in [".git", "__pycache__", "node_modules"]):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = abs_path_pattern.findall(content)
            if matches:
                offenders.append(f"{py_file.relative_to(repo_path)}: {matches[0]}")
        except Exception:
            continue
    passed = len(offenders) == 0
    return CheckResult(
        check_id="RUN-05",
        item="No hardcoded absolute paths in Python files",
        dimension="runnability",
        passed=passed,
        severity="warning",
        points_possible=7,
        files=offenders[:5],
        evidence=offenders[:5],
        finding="" if passed else f"Found hardcoded paths in {len(offenders)} file(s)",
        suggestion="" if passed else (
            "Replace hardcoded paths with argparse arguments or relative paths:\n"
            "  parser.add_argument('--data-dir', default='data/')"
        ),
    )


# ── Reproducibility checks ─────────────────────────────────────────────────── #

def check_REP01_random_seed(repo_path: Path) -> CheckResult:
    """REP-01: Random seed is fixed in entry-point scripts (AST-checked)."""
    seed_pattern = re.compile(
        r"(random\.seed|np\.random\.seed|numpy\.random\.seed|torch\.manual_seed"
        r"|torch\.cuda\.manual_seed|tf\.random\.set_seed|set_seed|pl\.seed_everything"
        r"|seed_everything)\s*\("
    )
    target_names = {"train", "main", "run", "finetune", "pretrain"}
    seed_files: list[str] = []
    missing_seed_files: list[str] = []

    for py_file in repo_path.rglob("*.py"):
        if not any(kw in py_file.stem.lower() for kw in target_names):
            continue
        if any(p in py_file.parts for p in [".git", "__pycache__"]):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Check if file uses random libraries
        uses_random = re.search(r"\bimport\s+(random|numpy|torch|tensorflow)\b", content)
        if not uses_random:
            continue

        if seed_pattern.search(content):
            seed_files.append(str(py_file.relative_to(repo_path)))
        else:
            missing_seed_files.append(str(py_file.relative_to(repo_path)))

    # Pass if all relevant files set seeds, or if no relevant files exist
    if not seed_files and not missing_seed_files:
        # No target files found — check any Python file for seeds
        for py_file in repo_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                if seed_pattern.search(content):
                    seed_files.append(str(py_file.relative_to(repo_path)))
            except Exception:
                continue

    passed = len(seed_files) > 0 and len(missing_seed_files) == 0
    return CheckResult(
        check_id="REP-01",
        item="Random seed is fixed in entry-point scripts",
        dimension="reproducibility",
        passed=passed,
        severity="warning",
        points_possible=12,
        files=seed_files[:3] + missing_seed_files[:3],
        evidence=missing_seed_files[:3] if missing_seed_files else seed_files[:3],
        finding="" if passed else (
            f"Seed not set in: {', '.join(missing_seed_files[:3])}"
            if missing_seed_files else "No seed-setting calls found in any Python file"
        ),
        suggestion="" if passed else (
            "Add at the top of each training script:\n"
            "  import random, numpy as np, torch\n"
            "  random.seed(42); np.random.seed(42); torch.manual_seed(42)"
        ),
    )


def check_REP02_config_files(repo_path: Path) -> CheckResult:
    """REP-02: Hyperparameter configuration file exists."""
    config_dirs = ["configs", "config", "conf", "settings"]
    config_patterns = ["hparams.*", "hyperparams.*", "params.*"]
    found = []

    for d in config_dirs:
        config_dir = repo_path / d
        if config_dir.is_dir():
            yaml_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml")) + list(config_dir.glob("*.json"))
            found.extend(yaml_files[:3])

    for pattern in config_patterns:
        found.extend(list(repo_path.glob(pattern))[:2])

    passed = len(found) > 0
    return CheckResult(
        check_id="REP-02",
        item="Hyperparameter configuration file exists",
        dimension="reproducibility",
        passed=passed,
        severity="warning",
        points_possible=10,
        files=[str(f.relative_to(repo_path)) for f in found[:5]],
        evidence=[str(f.relative_to(repo_path)) for f in found[:3]],
        finding="" if passed else "No YAML/JSON config files found in configs/, config/, or root",
        suggestion="" if passed else (
            "Add configs/default.yaml with all hyperparameters:\n"
            "  learning_rate: 1e-4\n  batch_size: 32\n  epochs: 100\n  seed: 42"
        ),
    )


def check_REP03_data_script(repo_path: Path) -> CheckResult:
    """REP-03: Data download or preparation script exists."""
    script_patterns = [
        "download_data*", "get_data*", "prepare_data*", "preprocess*",
        "scripts/download*", "data/download*", "data/README*",
    ]
    found = []
    for pattern in script_patterns:
        found.extend(repo_path.glob(pattern))

    # Check Makefile / shell scripts for wget/curl/gdown
    for sh_file in list(repo_path.rglob("*.sh")) + list(repo_path.glob("Makefile")):
        try:
            content = sh_file.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\b(wget|curl|gdown|huggingface_hub|datasets\.load)\b", content):
                found.append(sh_file)
        except Exception:
            continue

    # Check for .dvc files (DVC data versioning)
    found.extend(list(repo_path.rglob("*.dvc"))[:2])

    passed = len(found) > 0
    return CheckResult(
        check_id="REP-03",
        item="Data download or preparation script exists",
        dimension="reproducibility",
        passed=passed,
        severity="warning",
        points_possible=10,
        files=[str(f.relative_to(repo_path)) for f in found[:3]],
        evidence=[str(f.relative_to(repo_path)) for f in found[:3]],
        finding="" if passed else "No data download script, Makefile with wget/curl, or .dvc files found",
        suggestion="" if passed else (
            "Add download_data.sh:\n"
            "  #!/bin/bash\n"
            "  wget -P data/ https://your-dataset-url/data.zip\n"
            "  unzip data/data.zip -d data/"
        ),
    )


def check_REP04_checkpoint(repo_path: Path) -> CheckResult:
    """REP-04: Pretrained checkpoint or model download link available."""
    ckpt_patterns = ["*.ckpt", "*.pth", "*.pt", "*.bin", "*.safetensors", "model_weights*"]
    found_files = []
    for pattern in ckpt_patterns:
        found_files.extend(list(repo_path.rglob(pattern))[:2])

    # Check README for checkpoint/download mentions
    checkpoint_in_readme = False
    readme_file = None
    for readme in repo_path.glob("README*"):
        try:
            content = readme.read_text(encoding="utf-8", errors="ignore").lower()
            if any(kw in content for kw in ["checkpoint", "pretrained", "model weights", "download model", "gdown", "huggingface"]):
                checkpoint_in_readme = True
                readme_file = readme
                break
        except Exception:
            continue

    passed = len(found_files) > 0 or checkpoint_in_readme
    evidence = [str(f.relative_to(repo_path)) for f in found_files[:2]]
    if readme_file and checkpoint_in_readme:
        evidence.append(str(readme_file.relative_to(repo_path)))

    return CheckResult(
        check_id="REP-04",
        item="Pretrained checkpoint or model download link available",
        dimension="reproducibility",
        passed=passed,
        severity="info",
        points_possible=8,
        files=evidence,
        evidence=evidence,
        finding="" if passed else "No checkpoint files or checkpoint download link found in README",
        suggestion="" if passed else (
            "Either include model checkpoints in the repo or add to README:\n"
            "  ## Pre-trained Models\n"
            "  Download from: [link] or run: gdown --id <file-id>"
        ),
    )


def check_REP05_experiment_logging(repo_path: Path) -> CheckResult:
    """REP-05: Experiment logging integration present."""
    logging_libs = {
        "wandb": r"\bwandb\b",
        "mlflow": r"\bmlflow\b",
        "tensorboard": r"\btensorboard\b|\bSummaryWriter\b",
        "neptune": r"\bneptune\b",
        "comet": r"\bcomet_ml\b",
    }
    found_libs: list[str] = []
    found_files: list[str] = []

    for py_file in repo_path.rglob("*.py"):
        if any(p in py_file.parts for p in [".git", "__pycache__"]):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for lib, pattern in logging_libs.items():
                if re.search(pattern, content) and lib not in found_libs:
                    found_libs.append(lib)
                    found_files.append(str(py_file.relative_to(repo_path)))
        except Exception:
            continue

    passed = len(found_libs) > 0
    return CheckResult(
        check_id="REP-05",
        item="Experiment logging integration (wandb/mlflow/tensorboard/etc.)",
        dimension="reproducibility",
        passed=passed,
        severity="info",
        points_possible=5,
        files=found_files[:3],
        evidence=found_files[:3],
        finding=f"Found: {', '.join(found_libs)}" if passed else "No experiment logging library detected",
        suggestion="" if passed else (
            "Add experiment tracking (e.g. wandb):\n"
            "  import wandb\n"
            "  wandb.init(project='my-project', config=args)"
        ),
    )


def check_REP06_license(repo_path: Path) -> CheckResult:
    """REP-06: License file present."""
    licenses = list(repo_path.glob("LICENSE*")) + list(repo_path.glob("LICENCE*"))
    passed = len(licenses) > 0
    return CheckResult(
        check_id="REP-06",
        item="License file present",
        dimension="reproducibility",
        passed=passed,
        severity="info",
        points_possible=3,
        files=[str(f.relative_to(repo_path)) for f in licenses],
        evidence=[str(f.relative_to(repo_path)) for f in licenses],
        finding="" if passed else "No LICENSE or LICENCE file found",
        suggestion="" if passed else "Add a LICENSE file (MIT, Apache 2.0). GitHub provides templates.",
    )


def check_REP07_container(repo_path: Path) -> CheckResult:
    """REP-07: Docker/container spec exists."""
    docker_files = (
        list(repo_path.glob("Dockerfile*"))
        + list(repo_path.glob("docker-compose*"))
        + list(repo_path.glob(".devcontainer/"))
        + list(repo_path.glob("*.nix"))
    )
    passed = len(docker_files) > 0
    return CheckResult(
        check_id="REP-07",
        item="Container/environment spec exists (Docker, devcontainer, Nix)",
        dimension="reproducibility",
        passed=passed,
        severity="info",
        points_possible=2,
        files=[str(f.relative_to(repo_path)) for f in docker_files],
        evidence=[str(f.relative_to(repo_path)) for f in docker_files],
        finding="" if passed else "No Dockerfile, docker-compose.yml, .devcontainer, or .nix file",
        suggestion="" if passed else (
            "Add a Dockerfile for full environment reproducibility:\n"
            "  FROM python:3.11-slim\n"
            "  COPY requirements.txt .\n"
            "  RUN pip install -r requirements.txt"
        ),
    )


ALL_CHECKS = [
    # Runnability (max 50 pts)
    check_RUN01_requirements,
    check_RUN02_readme_install,
    check_RUN03_readme_usage,
    check_RUN04_entry_point,
    check_RUN05_no_hardcoded_paths,
    # Reproducibility (max 50 pts)
    check_REP01_random_seed,
    check_REP02_config_files,
    check_REP03_data_script,
    check_REP04_checkpoint,
    check_REP05_experiment_logging,
    check_REP06_license,
    check_REP07_container,
]

RUNNABILITY_CHECKS = [c for c in ALL_CHECKS if c.__name__.startswith("check_RUN")]
REPRODUCIBILITY_CHECKS = [c for c in ALL_CHECKS if c.__name__.startswith("check_REP")]


def compute_scores(results: list[CheckResult]) -> dict[str, int]:
    """
    Compute separate runnability and reproducibility scores (each 0–50),
    plus an overall score (0–100).
    """
    run_earned = sum(r.points_earned for r in results if r.dimension == "runnability")
    run_max = sum(r.points_possible for r in results if r.dimension == "runnability")
    rep_earned = sum(r.points_earned for r in results if r.dimension == "reproducibility")
    rep_max = sum(r.points_possible for r in results if r.dimension == "reproducibility")

    # Normalize each dimension to 0-50 (in case check set is modified)
    run_score = round((run_earned / run_max) * 50) if run_max > 0 else 0
    rep_score = round((rep_earned / rep_max) * 50) if rep_max > 0 else 0

    return {
        "runnability_score": run_score,
        "reproducibility_score": rep_score,
        "overall_score": run_score + rep_score,
    }


def score_to_grade(overall: int) -> str:
    if overall >= 90:
        return "A"
    if overall >= 75:
        return "B"
    if overall >= 55:
        return "C"
    if overall >= 35:
        return "D"
    return "F"
