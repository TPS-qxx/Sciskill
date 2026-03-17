"""
PDF parsing utilities.

Primary backend: PyMuPDF (fitz) — lightweight, no server required.
Optional backend: GROBID — higher accuracy for structured academic PDF parsing.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class ParsedSection(NamedTuple):
    heading: str
    content: str


class ParsedPaper(NamedTuple):
    title: str
    abstract: str
    sections: list[ParsedSection]
    full_text: str
    metadata: dict


# ------------------------------------------------------------------ #
# PyMuPDF backend                                                      #
# ------------------------------------------------------------------ #

def parse_pdf_pymupdf(pdf_path: str | Path) -> ParsedPaper:
    """
    Parse a PDF with PyMuPDF.
    Returns a ParsedPaper with title, abstract, sections, and full text.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PyMuPDF is required: pip install pymupdf"
        ) from e

    pdf_path = Path(pdf_path)
    doc = fitz.open(str(pdf_path))

    blocks_by_page: list[list[dict]] = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        blocks_by_page.append(blocks)

    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    title, abstract, sections = _segment_paper_text(full_text)

    return ParsedPaper(
        title=title,
        abstract=abstract,
        sections=sections,
        full_text=full_text,
        metadata={"source": "pymupdf", "path": str(pdf_path)},
    )


def _segment_paper_text(text: str) -> tuple[str, str, list[ParsedSection]]:
    """
    Heuristic section segmentation for academic papers.
    Returns (title, abstract, sections).
    """
    lines = text.split("\n")

    # Title: first non-empty line(s) before Abstract
    title_lines: list[str] = []
    abstract_lines: list[str] = []
    in_abstract = False
    abstract_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if not title_lines:
            title_lines.append(stripped)
            continue
        if re.match(r"^\s*abstract\s*$", stripped, re.IGNORECASE):
            in_abstract = True
            abstract_start = i
            continue
        if in_abstract:
            # Stop abstract at next section heading
            if re.match(r"^\d+[\.\s]|^[A-Z][A-Z\s]{3,}$", stripped):
                break
            abstract_lines.append(stripped)

    title = " ".join(title_lines[:3])  # cap at 3 lines
    abstract = " ".join(abstract_lines)

    # Section segmentation using common heading patterns
    section_pattern = re.compile(
        r"^(\d+[\.\s]+[A-Z]|\b(?:Introduction|Related Work|Background|Methodology|"
        r"Method|Approach|Experiments?|Results?|Discussion|Conclusion|"
        r"References?|Acknowledgements?|Appendix)\b)",
        re.IGNORECASE,
    )

    sections: list[ParsedSection] = []
    current_heading = "body"
    current_lines: list[str] = []

    for line in lines[abstract_start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if section_pattern.match(stripped) and len(stripped) < 100:
            if current_lines:
                sections.append(ParsedSection(current_heading, " ".join(current_lines)))
            current_heading = stripped
            current_lines = []
        else:
            current_lines.append(stripped)

    if current_lines:
        sections.append(ParsedSection(current_heading, " ".join(current_lines)))

    return title, abstract, sections


# ------------------------------------------------------------------ #
# GROBID backend (optional, higher accuracy)                           #
# ------------------------------------------------------------------ #

def parse_pdf_grobid(pdf_path: str | Path, grobid_url: str = "http://localhost:8070") -> ParsedPaper:
    """
    Parse a PDF using GROBID TEI XML output.

    Requires GROBID running locally:
        docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
    """
    import httpx
    from xml.etree import ElementTree as ET

    pdf_path = Path(pdf_path)
    with open(pdf_path, "rb") as f:
        resp = httpx.post(
            f"{grobid_url}/api/processFulltextDocument",
            files={"input": f},
            timeout=120,
        )
    resp.raise_for_status()

    tei_xml = resp.text
    root = ET.fromstring(tei_xml)
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    def text(el):
        return "".join(el.itertext()).strip() if el is not None else ""

    title = text(root.find(".//tei:titleStmt/tei:title", ns))
    abstract_el = root.find(".//tei:abstract", ns)
    abstract = text(abstract_el)

    sections: list[ParsedSection] = []
    for div in root.findall(".//tei:body/tei:div", ns):
        head = div.find("tei:head", ns)
        heading = text(head) if head is not None else "unnamed"
        body_text = " ".join(text(p) for p in div.findall("tei:p", ns))
        if body_text:
            sections.append(ParsedSection(heading, body_text))

    full_text = title + "\n" + abstract + "\n" + "\n".join(
        f"{s.heading}\n{s.content}" for s in sections
    )

    return ParsedPaper(
        title=title,
        abstract=abstract,
        sections=sections,
        full_text=full_text,
        metadata={"source": "grobid", "path": str(pdf_path)},
    )


def parse_pdf(
    pdf_path: str | Path,
    backend: str = "pymupdf",
    grobid_url: str = "http://localhost:8070",
) -> ParsedPaper:
    """Unified PDF parsing entry point."""
    if backend == "grobid":
        return parse_pdf_grobid(pdf_path, grobid_url=grobid_url)
    return parse_pdf_pymupdf(pdf_path)
