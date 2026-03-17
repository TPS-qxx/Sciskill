"""
Skill 6: Reproducibility Checker

Inputs:
  - repo_url: GitHub repository URL
  - local_path: local path to a cloned repo (alternative to repo_url)
  - cleanup: bool (default True) — remove cloned repo after analysis

Output:
  {
    "repo": "owner/name",
    "score": 72,
    "checks": [...],
    "suggestions": [...],
    "summary": "..."
  }
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
    compute_score,
)
from sciskills.utils.llm_client import get_default_client


@registry.register
class ReproducibilityChecker(BaseSkill):
    name = "reproducibility_checker"
    description = (
        "Analyze a GitHub repository for common reproducibility issues. "
        "Checks for: dependency files, random seed fixation, hardcoded paths, "
        "data download scripts, README quality, and more. "
        "Returns a reproducibility score (0-100) and actionable suggestions."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "GitHub repository URL, e.g. 'https://github.com/owner/repo'.",
            },
            "local_path": {
                "type": "string",
                "description": "Path to a locally cloned repository.",
            },
            "cleanup": {
                "type": "boolean",
                "default": True,
                "description": "Remove the cloned repo after analysis (only applies when repo_url is used).",
            },
            "generate_summary": {
                "type": "boolean",
                "default": True,
                "description": "Generate an LLM summary of the reproducibility report.",
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
            "repo": {"type": "string"},
            "score": {"type": "integer"},
            "checks": {"type": "array"},
            "suggestions": {"type": "array"},
            "summary": {"type": "string"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        repo_label = ""
        tmp_dir: str | None = None

        try:
            if "local_path" in params:
                repo_path = Path(params["local_path"])
                repo_label = repo_path.name
            else:
                repo_url = params["repo_url"].rstrip("/")
                repo_label = self._parse_repo_label(repo_url)
                tmp_dir = tempfile.mkdtemp(prefix="sciskills_repro_")
                repo_path = Path(tmp_dir) / "repo"
                self._clone_repo(repo_url, repo_path)

            # Run all checks
            results: list[CheckResult] = []
            for check_fn in ALL_CHECKS:
                try:
                    results.append(check_fn(repo_path))
                except Exception as e:
                    results.append(CheckResult(
                        item=check_fn.__name__,
                        passed=False,
                        severity="info",
                        detail=f"Check failed with error: {e}",
                    ))

            score = compute_score(results)
            suggestions = [r.suggestion for r in results if not r.passed and r.suggestion]

            checks_dicts = [
                {
                    "item": r.item,
                    "passed": r.passed,
                    "severity": r.severity,
                    "files": r.files,
                    "detail": r.detail,
                    "suggestion": r.suggestion,
                }
                for r in results
            ]

            summary = ""
            if params.get("generate_summary", True):
                summary = self._generate_summary(repo_label, score, results, suggestions)

            return SkillResult.ok(
                data={
                    "repo": repo_label,
                    "score": score,
                    "checks": checks_dicts,
                    "suggestions": suggestions,
                    "summary": summary,
                    "stats": {
                        "total_checks": len(results),
                        "passed": sum(1 for r in results if r.passed),
                        "failed": sum(1 for r in results if not r.passed),
                    },
                }
            )

        except Exception as e:
            return SkillResult.fail(errors=[str(e)])

        finally:
            if tmp_dir and params.get("cleanup", True):
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
                "Make sure the repository is public and git is installed."
            )

    def _generate_summary(
        self,
        repo: str,
        score: int,
        results: list[CheckResult],
        suggestions: list[str],
    ) -> str:
        failed_items = [r.item for r in results if not r.passed]
        passed_items = [r.item for r in results if r.passed]

        prompt = f"""You are reviewing the reproducibility of a machine learning research repository.

Repository: {repo}
Reproducibility Score: {score}/100

Passed checks ({len(passed_items)}): {', '.join(passed_items[:6])}
Failed checks ({len(failed_items)}): {', '.join(failed_items[:6])}

Top suggestions:
{chr(10).join(f'- {s[:100]}' for s in suggestions[:5])}

Write a concise 3-4 sentence summary that:
1. States the overall reproducibility level (excellent/good/moderate/poor based on score)
2. Highlights the most critical issues
3. Gives the top 1-2 actionable recommendations

Keep it factual and constructive."""

        try:
            llm = get_default_client()
            return llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
        except Exception:
            level = (
                "excellent" if score >= 85
                else "good" if score >= 70
                else "moderate" if score >= 50
                else "poor"
            )
            return (
                f"Reproducibility level: {level} (score: {score}/100). "
                f"Failed {len(failed_items)} checks. "
                f"Priority: {suggestions[0] if suggestions else 'No specific issues.'}"
            )
