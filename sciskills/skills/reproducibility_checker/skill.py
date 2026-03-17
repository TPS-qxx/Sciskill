"""
Skill 6: Reproducibility Checker

Two-dimension scoring:
  - runnability_score (0-50): can someone install and run the code?
  - reproducibility_score (0-50): can someone re-obtain the paper's numbers?
  - overall_score (0-100) = sum of both dimensions

Each check has a canonical check_id (RUN-01…RUN-05, REP-01…REP-07),
transparent point weights, and a copy-paste fix suggestion.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.skills.reproducibility_checker.checks import (
    ALL_CHECKS,
    CheckResult,
    compute_scores,
    score_to_grade,
)
from sciskills.utils.llm_client import get_default_client


@registry.register
class ReproducibilityChecker(BaseSkill):
    name = "reproducibility_checker"
    description = (
        "Static-analysis reproducibility audit for ML repositories. "
        "Returns runnability_score (0-50) and reproducibility_score (0-50) separately, "
        "a per-check breakdown with transparent point weights and fix suggestions. "
        "Checks: dependency files, README quality, seed fixation, config files, "
        "data scripts, checkpoints, experiment logging, Docker support."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "GitHub/GitLab HTTPS URL, e.g. 'https://github.com/owner/repo'.",
            },
            "local_path": {
                "type": "string",
                "description": "Absolute path to a locally cloned repository.",
            },
            "keep_clone": {
                "type": "boolean",
                "default": False,
                "description": "Keep the cloned repo after analysis (only applies to repo_url).",
            },
            "checks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Subset of check_ids to run (e.g. ['RUN-01','REP-01']). Default: all.",
            },
            "strict_mode": {
                "type": "boolean",
                "default": False,
                "description": "Treat 'warning' checks as errors in score calculation.",
            },
        },
        "oneOf": [
            {"required": ["repo_url"]},
            {"required": ["local_path"]},
        ],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "runnability_score": {"type": "integer"},
            "reproducibility_score": {"type": "integer"},
            "overall_score": {"type": "integer"},
            "grade": {"type": "string"},
            "checks": {"type": "array"},
            "dimension_breakdown": {"type": "object"},
            "warnings": {"type": "array"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        repo_label = ""
        tmp_dir: str | None = None
        process_warnings: list[str] = []

        try:
            if "local_path" in params:
                repo_path = Path(params["local_path"])
                repo_label = repo_path.name
                if not repo_path.is_dir():
                    return SkillResult.fail(errors=[f"Directory not found: {repo_path}"])
            else:
                repo_url = params["repo_url"].rstrip("/")
                repo_label = self._parse_repo_label(repo_url)
                tmp_dir = tempfile.mkdtemp(prefix="sciskills_repro_")
                repo_path = Path(tmp_dir) / "repo"
                self._clone_repo(repo_url, repo_path)

            # Filter checks if subset requested
            filter_ids = set(params.get("checks") or [])
            check_fns = [
                fn for fn in ALL_CHECKS
                if not filter_ids or fn.__name__.split("_")[1].upper() in filter_ids
                   or any(fn.__name__.upper().startswith(f"CHECK_{cid.replace('-', '_')}") for cid in filter_ids)
            ]
            if filter_ids:
                # Simple match: check if check_id appears in function name
                check_fns = [
                    fn for fn in ALL_CHECKS
                    if any(cid.replace("-", "_").lower() in fn.__name__.lower() for cid in filter_ids)
                ]
            if not check_fns:
                check_fns = ALL_CHECKS

            # Run all checks
            results: list[CheckResult] = []
            for check_fn in check_fns:
                try:
                    results.append(check_fn(repo_path))
                except Exception as e:
                    process_warnings.append(f"{check_fn.__name__} failed: {e}")

            scores = compute_scores(results)
            grade = score_to_grade(scores["overall_score"])

            checks_dicts = [
                {
                    "check_id": r.check_id,
                    "dimension": r.dimension,
                    "severity": r.severity,
                    "passed": r.passed,
                    "points_possible": r.points_possible,
                    "points_earned": r.points_earned,
                    "description": r.item,
                    "finding": r.finding,
                    "fix_suggestion": r.suggestion,
                    "evidence": r.evidence,
                }
                for r in results
            ]

            def dim_stats(dim: str) -> dict:
                dim_results = [r for r in results if r.dimension == dim]
                earned = sum(r.points_earned for r in dim_results)
                possible = sum(r.points_possible for r in dim_results)
                passed_count = sum(1 for r in dim_results if r.passed)
                return {
                    "score": scores[f"{dim}_score"],
                    "max": possible,
                    "pct": round(earned / possible * 100, 1) if possible > 0 else 0.0,
                    "checks_passed": passed_count,
                    "checks_failed": len(dim_results) - passed_count,
                }

            return SkillResult.ok(
                data={
                    "repo": repo_label,
                    "runnability_score": scores["runnability_score"],
                    "reproducibility_score": scores["reproducibility_score"],
                    "overall_score": scores["overall_score"],
                    "grade": grade,
                    "checks": checks_dicts,
                    "dimension_breakdown": {
                        "runnability": dim_stats("runnability"),
                        "reproducibility": dim_stats("reproducibility"),
                    },
                    "warnings": process_warnings,
                }
            )

        except Exception as e:
            return SkillResult.fail(errors=[str(e)])

        finally:
            if tmp_dir and not params.get("keep_clone", False):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------ #

    def _parse_repo_label(self, url: str) -> str:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return url

    def _clone_repo(self, url: str, dest: Path) -> None:
        """Shallow clone the repository."""
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git clone failed: {result.stderr.strip()}\n"
                "Ensure the repository is public and git is installed."
            )
