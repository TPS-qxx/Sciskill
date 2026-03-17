#!/usr/bin/env python3
"""
Utility: merge multiple paper JSON files (from paper-structural-extractor)
into a single {"papers": [...]} JSON object.

Usage:
    python merge_papers.py paper1.json paper2.json paper3.json > papers.json
    python merge_papers.py /tmp/paper*.json > papers.json
"""
import json
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_papers.py paper1.json paper2.json ... > papers.json",
              file=sys.stderr)
        sys.exit(1)

    papers = []
    for path in sys.argv[1:]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # Handle both {"paper": {...}} and plain {...}
            if "paper" in data:
                papers.append(data["paper"])
            elif isinstance(data, dict) and "title" in data:
                papers.append(data)
            else:
                print(f"Warning: could not parse paper from {path}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: skipping {path}: {e}", file=sys.stderr)

    print(json.dumps({"papers": papers}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
