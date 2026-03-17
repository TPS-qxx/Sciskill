#!/usr/bin/env python3
"""
CLI entry point for the reproducibility-checker skill.

Usage:
    python run.py --repo https://github.com/owner/repo
    python run.py --local /path/to/project
    python run.py --repo https://github.com/owner/repo --keep --no-summary
"""
import argparse
import json
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main():
    parser = argparse.ArgumentParser(description="Check a repository for reproducibility issues.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", metavar="URL",
                       help="GitHub repository URL to analyze")
    group.add_argument("--local", metavar="PATH",
                       help="Local repository path to analyze")
    parser.add_argument("--keep", action="store_true",
                        help="Keep the cloned repo after analysis (only with --repo)")
    parser.add_argument("--no-summary", action="store_true",
                        help="Skip LLM-generated summary")
    args = parser.parse_args()

    try:
        from sciskills.skills.reproducibility_checker import ReproducibilityChecker
    except ImportError:
        print('{"error": "sciskills not installed. Run: pip install -e ."}', file=sys.stderr)
        sys.exit(1)

    params = {"generate_summary": not args.no_summary}
    if args.repo:
        params["repo_url"] = args.repo
        params["cleanup"] = not args.keep
    else:
        params["local_path"] = args.local

    skill = ReproducibilityChecker()
    result = skill(params)

    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
