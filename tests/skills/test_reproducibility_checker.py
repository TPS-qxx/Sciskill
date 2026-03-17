"""Tests for ReproducibilityChecker — uses a temp directory (no git clone)."""
import tempfile
from pathlib import Path

import pytest

from sciskills.skills.reproducibility_checker.checks import (
    check_RUN01_requirements,
    check_RUN02_readme_install,
    check_RUN03_readme_usage,
    check_RUN04_entry_point,
    check_RUN05_no_hardcoded_paths,
    check_REP01_random_seed,
    check_REP06_license,
    compute_scores,
    CheckResult,
)
from sciskills.skills.reproducibility_checker import ReproducibilityChecker


@pytest.fixture
def tmp_repo(tmp_path):
    return tmp_path


# ------------------------------------------------------------------ #
# Individual check tests                                               #
# ------------------------------------------------------------------ #

def test_requirements_missing(tmp_repo):
    r = check_RUN01_requirements(tmp_repo)
    assert r.passed is False
    assert r.check_id == "RUN-01"
    assert r.dimension == "runnability"
    assert r.points_earned == 0


def test_requirements_present(tmp_repo):
    (tmp_repo / "requirements.txt").write_text("numpy>=1.20\ntorch>=2.0\n")
    r = check_RUN01_requirements(tmp_repo)
    assert r.passed is True
    assert r.points_earned == r.points_possible


def test_readme_install_missing(tmp_repo):
    r = check_RUN02_readme_install(tmp_repo)
    assert r.passed is False
    assert r.check_id == "RUN-02"


def test_readme_install_present(tmp_repo):
    (tmp_repo / "README.md").write_text("# Project\n\n## Installation\npip install .\n")
    r = check_RUN02_readme_install(tmp_repo)
    assert r.passed is True


def test_readme_usage_present(tmp_repo):
    (tmp_repo / "README.md").write_text("# Project\n\n## Installation\npip install .\n\n## Usage\npython train.py\n")
    r = check_RUN03_readme_usage(tmp_repo)
    assert r.passed is True


def test_random_seed_found(tmp_repo):
    (tmp_repo / "train.py").write_text("import torch\ntorch.manual_seed(42)\n")
    r = check_REP01_random_seed(tmp_repo)
    assert r.passed is True
    assert r.check_id == "REP-01"
    assert r.dimension == "reproducibility"


def test_random_seed_missing(tmp_repo):
    (tmp_repo / "train.py").write_text("import torch\nmodel = torch.nn.Linear(10, 5)\n")
    r = check_REP01_random_seed(tmp_repo)
    assert r.passed is False
    assert r.suggestion != ""  # should have a fix suggestion


def test_hardcoded_path_found(tmp_repo):
    (tmp_repo / "data.py").write_text('data_path = "/home/user/datasets/mydata"\n')
    r = check_RUN05_no_hardcoded_paths(tmp_repo)
    assert r.passed is False
    assert r.check_id == "RUN-05"


def test_no_hardcoded_paths(tmp_repo):
    (tmp_repo / "data.py").write_text('data_path = "data/mydata"\n')
    r = check_RUN05_no_hardcoded_paths(tmp_repo)
    assert r.passed is True


def test_license_present(tmp_repo):
    (tmp_repo / "LICENSE").write_text("MIT License\n")
    r = check_REP06_license(tmp_repo)
    assert r.passed is True
    assert r.check_id == "REP-06"


# ------------------------------------------------------------------ #
# Score computation                                                    #
# ------------------------------------------------------------------ #

def _make_result(check_id: str, dimension: str, passed: bool, possible: int) -> CheckResult:
    r = CheckResult(
        check_id=check_id,
        item="Test check",
        dimension=dimension,
        passed=passed,
        severity="error",
        points_possible=possible,
    )
    return r


def test_scores_all_passed():
    results = [
        _make_result("RUN-01", "runnability", True, 15),
        _make_result("RUN-02", "runnability", True, 10),
        _make_result("REP-01", "reproducibility", True, 12),
        _make_result("REP-02", "reproducibility", True, 10),
    ]
    scores = compute_scores(results)
    assert scores["runnability_score"] == 50  # 25/25 → normalized to 50
    assert scores["reproducibility_score"] == 50  # 22/22 → normalized to 50
    assert scores["overall_score"] == 100


def test_scores_partial():
    results = [
        _make_result("RUN-01", "runnability", True, 15),
        _make_result("RUN-02", "runnability", False, 10),  # fail
        _make_result("REP-01", "reproducibility", False, 12),  # fail
        _make_result("REP-02", "reproducibility", True, 10),
    ]
    scores = compute_scores(results)
    # runnability: 15/25 = 60% → 30/50
    assert scores["runnability_score"] == 30
    # reproducibility: 10/22 ≈ 45% → 23/50
    assert scores["reproducibility_score"] == 23
    assert scores["overall_score"] == 53


# ------------------------------------------------------------------ #
# Skill integration test (local path)                                  #
# ------------------------------------------------------------------ #

def test_skill_local_repo(tmp_repo):
    # Create a minimal "good" repo
    (tmp_repo / "requirements.txt").write_text("numpy\n")
    (tmp_repo / "README.md").write_text(
        "# Repo\n\n## Installation\npip install .\n\n## Usage\npython train.py\n"
    )
    (tmp_repo / "LICENSE").write_text("MIT\n")
    (tmp_repo / "train.py").write_text(
        "import torch\ntorch.manual_seed(42)\nmodel = torch.nn.Linear(10, 5)\n"
    )

    skill = ReproducibilityChecker()
    result = skill({"local_path": str(tmp_repo)})

    assert result.success
    assert "runnability_score" in result.data
    assert "reproducibility_score" in result.data
    assert "overall_score" in result.data
    assert "grade" in result.data
    assert isinstance(result.data["checks"], list)
    assert len(result.data["checks"]) > 0
    # Each check should have required fields
    for check in result.data["checks"]:
        assert "check_id" in check
        assert "dimension" in check
        assert "passed" in check
        assert "points_possible" in check
        assert "points_earned" in check


def test_skill_output_structure(tmp_repo):
    skill = ReproducibilityChecker()
    result = skill({"local_path": str(tmp_repo)})
    assert result.success
    data = result.data
    assert "dimension_breakdown" in data
    assert "runnability" in data["dimension_breakdown"]
    assert "reproducibility" in data["dimension_breakdown"]
    run_dim = data["dimension_breakdown"]["runnability"]
    assert "score" in run_dim
    assert "max" in run_dim
    assert "pct" in run_dim
    assert "checks_passed" in run_dim
    assert "checks_failed" in run_dim
