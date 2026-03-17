#!/usr/bin/env python3
"""
CLI entry point for the paper-structural-extractor skill.
Prints a JSON object to stdout; errors go to stderr.

Usage:
    python run.py --arxiv 2303.08774
    python run.py --doi 10.1145/3292500.3330919
    python run.py --pdf /path/to/paper.pdf [--backend grobid]
"""
import argparse
import json
import os
import sys

# Allow running from project root or from inside the skill directory
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)


def main():
    parser = argparse.ArgumentParser(description="Extract structured info from an academic paper.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--arxiv", metavar="ID", help="arXiv paper ID, e.g. 2303.08774")
    group.add_argument("--doi", metavar="DOI", help="DOI, e.g. 10.1145/3292500.3330919")
    group.add_argument("--pdf", metavar="PATH", help="Local path to a PDF file")
    parser.add_argument("--backend", choices=["pymupdf", "grobid"], default="pymupdf",
                        help="PDF parsing backend (only used with --pdf)")
    parser.add_argument("--grobid-url", default="http://localhost:8070",
                        help="GROBID server URL (only used with --backend grobid)")
    args = parser.parse_args()

    try:
        from sciskills.skills.paper_extractor import PaperStructuralExtractor
    except ImportError:
        print(
            '{"error": "sciskills package not found. Run: pip install -e . from the project root"}',
            file=sys.stderr,
        )
        sys.exit(1)

    params = {}
    if args.arxiv:
        params["arxiv_id"] = args.arxiv
    elif args.doi:
        params["doi"] = args.doi
    else:
        params["pdf_path"] = args.pdf
        params["pdf_backend"] = args.backend
        params["grobid_url"] = args.grobid_url

    skill = PaperStructuralExtractor()
    result = skill(params)

    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": result.errors}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
