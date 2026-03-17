"""Tests for ReproducibilityChecker — uses a temp directory (no git clone)."""
import textwrap
import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch

from sciskills.skills.reproducibility_checker.checks import (
    check_requirements_file,
    check_random_seeds,
    check_hardcoded_paths,
    check_readme,
    check_license,
    compute_score,
    CheckResult,
)
from sciskills.skills.reproducibility_checker import ReproducibilityChecker


@pytest.fixture
def tmp_repo(tmp_path):
    """Return a temporary repo directory."""
    return tmp_path


# ------------------------------------------------------------------ #
# Individual check tests                                               #
# ------------------------------------------------------------------ #

def test_requirements_missing(tmp_repo):
    r = check_requirements_file(tmp_repo)
    assert r.passed is False


def test_requirements_present(tmp_repo):
    (tmp_repo / "requirements.txt").write_text("numpy>=1.20\ntorch>=2.0\n")
    r = check_requirements_file(tmp_repo)
    assert r.passed is True


def test_random_seed_found(tmp_repo):
    (tmp_repo / "train.py").write_text("import torch\ntorch.manual_seed(42)\n")
    r = check_random_seeds(tmp_repo)
    assert r.passed is True
    assert "train.py" in r.files[0]


def test_random_seed_missing(tmp_repo):
    (tmp_repo / "train.py").write_text("import torch\nmodel = torch.nn.Linear(10, 5)\n")
    r = check_random_seeds(tmp_repo)
    assert r.passed is False


def test_hardcoded_path_found(tmp_repo):
    (tmp_repo / "data.py").write_text('data_path = "/home/user/datasets/mydata"\n')
    r = check_hardcoded_paths(tmp_repo)
    assert r.passed is False


def test_no_hardcoded_paths(tmp_repo):
    (tmp_repo / "data.py").write_text('data_path = "data/mydata"\n')
    r = check_hardcoded_paths(tmp_repo)
    assert r.passed is True


def test_readme_missing(tmp_repo):
    r = check_readme(tmp_repo)
    assert r.passed is False


def test_readme_minimal(tmp_repo):
    (tmp_repo / "README.md").write_text("# Project\n\n## Installation\npip install .\n\n## Usage\npython run.py\n")
    r = check_readme(tmp_repo)
    assert r.passed is True


def test_license_present(tmp_repo):
    (tmp_repo / "LICENSE").write_text("MIT License\n")
    r = check_license(tmp_repo)
    assert r.passed is True


def test_score_perfect(tmp_repo):
    results = [CheckResult("A", True, "error"), CheckResult("B", True, "warning")]
    assert compute_score(results) == 100


def test_score_deductions(tmp_repo):
    results = [
        CheckResult("A", False, "error"),    # -15
        CheckResult("B", False, "warning"),  # -7
        CheckResult("C", True, "info"),      # 0
    ]
    assert compute_score(results) == 100 - 15 - 7


# ------------------------------------------------------------------ #
# Skill integration test (local path)                                  #
# ------------------------------------------------------------------ #

def test_skill_local_repo(tmp_repo):
    # Create a minimal "good" repo
    (tmp_repo / "requirements.txt").write_text("numpy\n")
    (tmp_repo / "README.md").write_text("# Repo\n\n## Installation\npip install .\n\n## Usage\npython train.py\n")
    (tmp_repo / "LICENSE").write_text("MIT\n")
    (tmp_repo / "train.py").write_text(
        "import torch\ntorch.manual_seed(42)\nmodel = torch.nn.Linear(10, 5)\n"
    )

    skill = ReproducibilityChecker()
    with patch.object(skill, "_generate_summary", return_value="Good repo."):
        result = skill({"local_path": str(tmp_repo)})

    assert result.success
    assert result.data["score"] > 0
    assert isinstance(result.data["checks"], list)
    assert len(result.data["checks"]) > 0
    assert result.data["summary"] == "Good repo."
