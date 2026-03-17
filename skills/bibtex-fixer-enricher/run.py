#!/usr/bin/env python3
"""
CLI entry point for the bibtex-fixer-enricher skill.

Usage:
    python run.py --bib refs.bib
    python run.py --bib refs.bib --no-enrich
    python run.py --bib refs.bib --keep-duplicates
    python run.py --bib refs.bib --no-normalize
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
    parser = argparse.ArgumentParser(description="Fix and enrich BibTeX entries.")
    parser.add_argument("--bib", metavar="PATH", required=True,
                        help="Path to .bib file")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip Crossref API enrichment (offline mode)")
    parser.add_argument("--keep-duplicates", action="store_true",
                        help="Do not remove detected duplicate entries")
    parser.add_argument("--no-normalize", action="store_true",
                        help="Do not normalize author name format")
    parser.add_argument("--format", choices=["json", "bibtex"], default="json",
                        help="Output format: full JSON report (default) or just the fixed BibTeX")
    args = parser.parse_args()

    try:
        from sciskills.skills.bibtex_fixer import BibTeXFixerEnricher
    except ImportError:
        print('{"error": "sciskills not installed. Run: pip install -e ."}', file=sys.stderr)
        sys.exit(1)

    skill = BibTeXFixerEnricher()
    result = skill({
        "bib_path": args.bib,
        "auto_enrich": not args.no_enrich,
        "remove_duplicates": not args.keep_duplicates,
        "normalize_authors": not args.no_normalize,
    })

    if result.success:
        if args.format == "bibtex":
            print(result.data["fixed_bibtex"])
        else:
            # Exclude the raw entries list to keep output readable
            output = {k: v for k, v in result.data.items() if k != "fixed_entries"}
            print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
