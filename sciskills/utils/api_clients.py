"""
Lightweight async/sync clients for academic metadata APIs.

Supported:
- Semantic Scholar (S2) API
- Crossref API
- OpenAlex API
- arXiv API
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

import httpx


_TIMEOUT = 20.0
_RATE_LIMIT_DELAY = 0.5  # seconds between requests


def _get(url: str, params: dict | None = None, headers: dict | None = None) -> dict:
    """Simple rate-limited GET returning JSON dict."""
    time.sleep(_RATE_LIMIT_DELAY)
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(url, params=params, headers=headers or {})
        resp.raise_for_status()
        return resp.json()


# ------------------------------------------------------------------ #
# Semantic Scholar                                                      #
# ------------------------------------------------------------------ #

class SemanticScholarClient:
    BASE = "https://api.semanticscholar.org/graph/v1"

    PAPER_FIELDS = (
        "title,authors,year,venue,externalIds,abstract,"
        "references,citations,tldr"
    )

    def __init__(self, api_key: str | None = None):
        self._headers = {"x-api-key": api_key} if api_key else {}

    def get_paper(self, paper_id: str) -> dict:
        """
        Fetch paper metadata.
        paper_id can be: S2 ID, arXiv:<id>, DOI:<doi>, etc.
        """
        url = f"{self.BASE}/paper/{quote(paper_id, safe=':')}"
        return _get(url, params={"fields": self.PAPER_FIELDS}, headers=self._headers)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search returning list of paper metadata dicts."""
        url = f"{self.BASE}/paper/search"
        data = _get(
            url,
            params={"query": query, "limit": limit, "fields": self.PAPER_FIELDS},
            headers=self._headers,
        )
        return data.get("data", [])

    def get_by_doi(self, doi: str) -> dict:
        return self.get_paper(f"DOI:{doi}")

    def get_by_arxiv(self, arxiv_id: str) -> dict:
        return self.get_paper(f"arXiv:{arxiv_id}")


# ------------------------------------------------------------------ #
# Crossref                                                             #
# ------------------------------------------------------------------ #

class CrossrefClient:
    BASE = "https://api.crossref.org"

    def get_by_doi(self, doi: str) -> dict:
        """Fetch metadata for a DOI from Crossref."""
        url = f"{self.BASE}/works/{quote(doi, safe='')}"
        data = _get(url, headers={"User-Agent": "SciSkills/0.1 (mailto:dev@sciskills.io)"})
        return data.get("message", {})

    def search(self, query: str, rows: int = 5) -> list[dict]:
        """Search Crossref for works matching query."""
        url = f"{self.BASE}/works"
        data = _get(
            url,
            params={"query": query, "rows": rows},
            headers={"User-Agent": "SciSkills/0.1"},
        )
        return data.get("message", {}).get("items", [])

    def bib_from_doi(self, doi: str) -> dict:
        """
        Return a flat dict of BibTeX-relevant fields for a DOI.
        """
        work = self.get_by_doi(doi)
        authors = [
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
            for a in work.get("author", [])
        ]
        issued = work.get("issued", {}).get("date-parts", [[None]])[0]
        year = issued[0] if issued else None

        container = (
            work.get("container-title", [""])[0]
            or work.get("event", {}).get("name", "")
        )

        return {
            "title": work.get("title", [""])[0],
            "author": " and ".join(authors),
            "year": str(year) if year else "",
            "journal": container,
            "volume": work.get("volume", ""),
            "number": work.get("issue", ""),
            "pages": work.get("page", ""),
            "doi": doi,
            "url": work.get("URL", ""),
            "publisher": work.get("publisher", ""),
        }


# ------------------------------------------------------------------ #
# OpenAlex                                                             #
# ------------------------------------------------------------------ #

class OpenAlexClient:
    BASE = "https://api.openalex.org"

    def get_by_doi(self, doi: str) -> dict:
        url = f"{self.BASE}/works/doi:{quote(doi, safe='')}"
        return _get(url, headers={"User-Agent": "SciSkills/0.1"})

    def search(self, query: str, per_page: int = 10) -> list[dict]:
        url = f"{self.BASE}/works"
        data = _get(
            url,
            params={"search": query, "per-page": per_page},
            headers={"User-Agent": "SciSkills/0.1"},
        )
        return data.get("results", [])


# ------------------------------------------------------------------ #
# arXiv                                                                #
# ------------------------------------------------------------------ #

class ArxivClient:
    BASE = "https://export.arxiv.org/api/query"

    def get_paper(self, arxiv_id: str) -> dict:
        """Fetch paper metadata from arXiv Atom feed."""
        # Normalize ID: strip version suffix for query
        clean_id = re.sub(r"v\d+$", "", arxiv_id.strip())
        params = {"id_list": clean_id, "max_results": 1}
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(self.BASE, params=params)
            resp.raise_for_status()
        return self._parse_atom(resp.text)

    def _parse_atom(self, xml_text: str) -> dict:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(xml_text)
        entry = root.find("atom:entry", ns)
        if entry is None:
            return {}

        def t(tag: str) -> str:
            el = entry.find(tag, ns)
            return el.text.strip() if el is not None and el.text else ""

        authors = [
            a.findtext("atom:name", namespaces=ns, default="").strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = t("atom:published")[:4]  # year
        arxiv_id_full = t("atom:id").split("/abs/")[-1]

        return {
            "arxiv_id": arxiv_id_full,
            "title": t("atom:title").replace("\n", " "),
            "abstract": t("atom:summary").replace("\n", " "),
            "authors": authors,
            "year": published,
            "primary_category": entry.findtext(
                "arxiv:primary_category", namespaces={**ns, "arxiv": "http://arxiv.org/schemas/atom"}, default=""
            ),
        }
