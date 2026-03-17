"""
Reproducibility check rules for GitHub repositories.
Based on NeurIPS Reproducibility Checklist + common ML practices.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    item: str
    passed: bool
    severity: str  # "error" | "warning" | "info"
    files: list[str] = field(default_factory=list)
    detail: str = ""
    suggestion: str = ""


def check_requirements_file(repo_path: Path) -> CheckResult:
    """Check for dependency specification files."""
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
        item="Dependency specification file exists",
        passed=passed,
        severity="error" if not passed else "info",
        files=[str(f.relative_to(repo_path)) for f in found],
        suggestion="Add requirements.txt or pyproject.toml listing all dependencies with versions."
        if not passed else "",
    )


def check_random_seeds(repo_path: Path) -> CheckResult:
    """Detect if random seeds are set in Python files."""
    seed_patterns = [
        r"random\.seed\s*\(",
        r"np\.random\.seed\s*\(",
        r"torch\.manual_seed\s*\(",
        r"torch\.cuda\.manual_seed",
        r"tf\.random\.set_seed\s*\(",
        r"set_seed\s*\(",
        r"seed\s*=\s*\d+",
    ]
    combined = re.compile("|".join(seed_patterns))

    seed_files: list[str] = []
    for py_file in repo_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if combined.search(content):
                seed_files.append(str(py_file.relative_to(repo_path)))
        except Exception:
            continue

    passed = len(seed_files) > 0
    return CheckResult(
        item="Random seed is fixed",
        passed=passed,
        severity="warning" if not passed else "info",
        files=seed_files[:5],
        suggestion=(
            "Fix random seeds for reproducibility:\n"
            "  import random, numpy as np, torch\n"
            "  random.seed(42); np.random.seed(42); torch.manual_seed(42)"
        )
        if not passed else "",
    )


def check_hardcoded_paths(repo_path: Path) -> CheckResult:
    """Detect hardcoded absolute paths in Python files."""
    abs_path_pattern = re.compile(r'["\'](?:/home/|/Users/|/root/|C:\\\\|/data/)[^"\']+["\']')
    offenders: list[str] = []

    for py_file in repo_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            matches = abs_path_pattern.findall(content)
            if matches:
                offenders.append(f"{py_file.relative_to(repo_path)}: {matches[0]}")
        except Exception:
            continue

    passed = len(offenders) == 0
    return CheckResult(
        item="No hardcoded absolute paths",
        passed=passed,
        severity="warning" if not passed else "info",
        files=offenders[:5],
        suggestion="Replace hardcoded paths with relative paths or argparse arguments."
        if not passed else "",
    )


def check_data_download_script(repo_path: Path) -> CheckResult:
    """Check for a data download or preprocessing script."""
    data_indicators = [
        "download_data*", "get_data*", "prepare_data*",
        "preprocess*", "data/README*", "data/download*",
        "scripts/download*", "Makefile",
    ]
    found = []
    for pattern in data_indicators:
        found.extend(repo_path.glob(pattern))
    # Also check for wget/curl calls
    for sh_file in list(repo_path.rglob("*.sh")) + list(repo_path.rglob("Makefile")):
        try:
            content = sh_file.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\bwget\b|\bcurl\b|\bgdown\b", content):
                found.append(sh_file)
        except Exception:
            continue

    passed = len(found) > 0
    return CheckResult(
        item="Data download/preparation script exists",
        passed=passed,
        severity="warning" if not passed else "info",
        files=[str(f.relative_to(repo_path)) for f in found[:3]],
        suggestion="Add a download_data.sh or Makefile with data acquisition commands."
        if not passed else "",
    )


def check_readme(repo_path: Path) -> CheckResult:
    """Check for a README with installation and usage instructions."""
    readmes = list(repo_path.glob("README*")) + list(repo_path.glob("readme*"))
    if not readmes:
        return CheckResult(
            item="README with setup instructions",
            passed=False,
            severity="error",
            suggestion="Add README.md with: installation, data preparation, training, evaluation instructions.",
        )

    readme = readmes[0]
    content = readme.read_text(encoding="utf-8", errors="ignore").lower()
    has_install = any(kw in content for kw in ["install", "requirements", "setup", "pip"])
    has_usage = any(kw in content for kw in ["usage", "run", "train", "evaluate", "example"])

    passed = has_install and has_usage
    return CheckResult(
        item="README with setup instructions",
        passed=passed,
        severity="warning" if not passed else "info",
        files=[str(readme.relative_to(repo_path))],
        suggestion="README should include: installation steps and usage/training/evaluation commands."
        if not passed else "",
    )


def check_model_checkpoint_info(repo_path: Path) -> CheckResult:
    """Check if pre-trained model checkpoints or download links are documented."""
    indicators = [
        "checkpoint*", "pretrained*", "model_weights*",
        "*.ckpt", "*.pth", "*.pt", "*.bin",
    ]
    found_ckpt = []
    for pattern in indicators:
        found_ckpt.extend(repo_path.glob(pattern))

    # Also check for checkpoint mentions in README
    checkpoint_in_docs = False
    for readme in repo_path.glob("README*"):
        content = readme.read_text(encoding="utf-8", errors="ignore").lower()
        if any(kw in content for kw in ["checkpoint", "pretrained", "model weights", "download model"]):
            checkpoint_in_docs = True
            break

    passed = len(found_ckpt) > 0 or checkpoint_in_docs
    return CheckResult(
        item="Model checkpoint or download link available",
        passed=passed,
        severity="info",
        files=[str(f.relative_to(repo_path)) for f in found_ckpt[:3]],
        suggestion="Include pre-trained model checkpoints or a download link in README."
        if not passed else "",
    )


def check_config_files(repo_path: Path) -> CheckResult:
    """Check for experiment configuration files."""
    config_patterns = [
        "config*", "configs/", "*.yaml", "*.yml", "*.json",
        "hparams*", "hyperparams*",
    ]
    found = []
    for pattern in config_patterns:
        found.extend(list(repo_path.glob(pattern))[:2])

    passed = len(found) > 0
    return CheckResult(
        item="Experiment configuration files exist",
        passed=passed,
        severity="info",
        files=[str(f.relative_to(repo_path)) for f in found[:5]],
        suggestion="Add config files (YAML/JSON) for all hyperparameters to enable exact reproduction."
        if not passed else "",
    )


def check_license(repo_path: Path) -> CheckResult:
    """Check for a LICENSE file."""
    licenses = list(repo_path.glob("LICENSE*")) + list(repo_path.glob("LICENCE*"))
    passed = len(licenses) > 0
    return CheckResult(
        item="License file exists",
        passed=passed,
        severity="info",
        files=[str(f.relative_to(repo_path)) for f in licenses],
        suggestion="Add a LICENSE file (MIT, Apache 2.0, etc.) for open-source compliance."
        if not passed else "",
    )


def check_docker_support(repo_path: Path) -> CheckResult:
    """Check for Docker/container support."""
    docker_files = (
        list(repo_path.glob("Dockerfile*"))
        + list(repo_path.glob("docker-compose*"))
        + list(repo_path.glob(".devcontainer/"))
    )
    passed = len(docker_files) > 0
    return CheckResult(
        item="Docker / container support",
        passed=passed,
        severity="info",
        files=[str(f.relative_to(repo_path)) for f in docker_files],
        suggestion="Consider adding a Dockerfile for full environment reproducibility."
        if not passed else "",
    )


def check_ast_seed_consistency(repo_path: Path) -> CheckResult:
    """
    Use AST analysis to check if all training/main scripts that import
    random/numpy/torch also call seed-setting functions.
    """
    suspicious: list[str] = []
    for py_file in repo_path.rglob("*.py"):
        name = py_file.stem.lower()
        if not any(kw in name for kw in ["train", "main", "run", "finetune"]):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except Exception:
            continue

        imports_random = any(
            (isinstance(node, ast.Import) and any(a.name in ("random", "numpy", "torch") for a in node.names))
            or (isinstance(node, ast.ImportFrom) and node.module in ("random", "numpy", "torch", "numpy.random"))
            for node in ast.walk(tree)
        )

        if not imports_random:
            continue

        has_seed = bool(re.search(
            r"(random|np|numpy|torch|tf)\..*seed|set_seed",
            source,
        ))
        if not has_seed:
            suspicious.append(str(py_file.relative_to(repo_path)))

    passed = len(suspicious) == 0
    return CheckResult(
        item="Training scripts set random seeds (AST check)",
        passed=passed,
        severity="warning" if not passed else "info",
        files=suspicious[:5],
        suggestion="Add seed initialization at the top of each training script."
        if not passed else "",
    )


ALL_CHECKS = [
    check_requirements_file,
    check_readme,
    check_random_seeds,
    check_ast_seed_consistency,
    check_hardcoded_paths,
    check_data_download_script,
    check_model_checkpoint_info,
    check_config_files,
    check_license,
    check_docker_support,
]

# Scoring weights
WEIGHTS = {
    "error": 15,
    "warning": 7,
    "info": 3,
}


def compute_score(results: list[CheckResult]) -> int:
    """
    Compute a 0-100 reproducibility score.
    Start at 100 and deduct points for failed checks.
    """
    total_deductions = 0
    for r in results:
        if not r.passed:
            total_deductions += WEIGHTS.get(r.severity, 5)
    return max(0, 100 - total_deductions)
