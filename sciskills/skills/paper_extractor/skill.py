"""
Skill 1: Paper Structural Extractor

Inputs:
  - arxiv_id OR doi OR pdf_path (one of these required)
  - pdf_backend: "pymupdf" | "grobid" (optional, default: "pymupdf")
  - grobid_url: str (optional)

Output:
  Full structured JSON with title, authors, research question, methodology,
  datasets, baselines, metrics, findings, limitations, future work.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.utils.api_clients import ArxivClient, SemanticScholarClient
from sciskills.utils.llm_client import get_default_client


_EXTRACT_PROMPT = """\
You are a scientific paper analysis assistant.
Given the following paper content, extract a structured JSON with EXACTLY this schema.
Return ONLY valid JSON, no explanation.

Schema:
{
  "title": "string",
  "authors": ["string"],
  "year": "string",
  "venue": "string",
  "research_question": "string - the core research question or objective",
  "problem_statement": "string - what problem is being solved",
  "methodology": {
    "approach": "string - high-level approach",
    "model_architecture": "string or null",
    "key_techniques": ["string"],
    "novelty": "string - what is novel about this approach"
  },
  "datasets": [
    {"name": "string", "scale": "string or null", "domain": "string or null", "public": true/false/null}
  ],
  "baselines": [
    {"name": "string", "source": "string or null", "paper_ref": "string or null"}
  ],
  "metrics": [
    {"name": "string", "value": "string or null", "dataset": "string or null", "is_best": false}
  ],
  "main_findings": ["string"],
  "limitations": ["string"],
  "future_work": ["string"],
  "related_work_summary": "string - brief summary of related work landscape",
  "implementation_details": {
    "code_available": true/false/null,
    "code_url": "string or null",
    "hardware": "string or null",
    "training_time": "string or null"
  }
}

Paper content:
---
{content}
---

Rules:
- Use null for any field you cannot determine from the paper.
- For metrics, if the paper reports multiple datasets, include one entry per dataset per metric.
- is_best should be true only if the paper explicitly claims SOTA or best results for that metric.
- Return only the JSON object, no markdown fences.
"""


@registry.register
class PaperStructuralExtractor(BaseSkill):
    name = "paper_structural_extractor"
    description = (
        "Extract structured information from an academic paper "
        "(research question, methodology, datasets, baselines, metrics, etc.) "
        "given an arXiv ID, DOI, or PDF path."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "arxiv_id": {
                "type": "string",
                "description": "arXiv paper ID, e.g. '2303.08774' or 'arxiv:2303.08774'",
            },
            "doi": {
                "type": "string",
                "description": "DOI string, e.g. '10.1145/3292500.3330919'",
            },
            "pdf_path": {
                "type": "string",
                "description": "Local path to a PDF file.",
            },
            "pdf_backend": {
                "type": "string",
                "enum": ["pymupdf", "grobid"],
                "default": "pymupdf",
                "description": "PDF parsing backend. 'grobid' is more accurate but requires a running GROBID server.",
            },
            "grobid_url": {
                "type": "string",
                "default": "http://localhost:8070",
                "description": "GROBID server URL (only used when pdf_backend='grobid').",
            },
            "llm_model": {
                "type": "string",
                "description": "Override the default LLM model for extraction.",
            },
        },
        "oneOf": [
            {"required": ["arxiv_id"]},
            {"required": ["doi"]},
            {"required": ["pdf_path"]},
        ],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "paper": {"type": "object"},
            "source": {"type": "string"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        try:
            content, source, meta = self._fetch_content(params)
            structured = self._extract_structure(content, params)
            # Merge metadata from API if available
            if meta:
                structured.setdefault("title", meta.get("title", ""))
                structured.setdefault("authors", meta.get("authors", []))
                structured.setdefault("year", str(meta.get("year", "")))
                structured.setdefault("venue", meta.get("venue", ""))

            return SkillResult.ok(
                data={"paper": structured, "source": source},
                metadata={"content_length": len(content)},
            )
        except Exception as e:
            return SkillResult.fail(errors=[str(e)])

    # ------------------------------------------------------------------ #

    def _fetch_content(self, params: dict) -> tuple[str, str, dict]:
        """Return (text_content, source_label, api_metadata)."""
        if "arxiv_id" in params:
            arxiv_id = params["arxiv_id"].replace("arxiv:", "").strip()
            client = ArxivClient()
            meta = client.get_paper(arxiv_id)
            # Also try semantic scholar for richer metadata
            try:
                s2 = SemanticScholarClient()
                s2_data = s2.get_by_arxiv(arxiv_id)
                meta.update({
                    "venue": s2_data.get("venue", ""),
                    "year": s2_data.get("year", meta.get("year", "")),
                })
            except Exception:
                pass
            content = f"Title: {meta.get('title', '')}\n\nAbstract: {meta.get('abstract', '')}"
            return content, f"arxiv:{arxiv_id}", meta

        if "doi" in params:
            doi = params["doi"]
            try:
                s2 = SemanticScholarClient()
                data = s2.get_by_doi(doi)
                abstract = (data.get("tldr") or {}).get("text", "") or data.get("abstract", "")
                content = f"Title: {data.get('title', '')}\n\nAbstract: {abstract}"
                meta = {
                    "title": data.get("title", ""),
                    "authors": [a.get("name", "") for a in data.get("authors", [])],
                    "year": data.get("year"),
                    "venue": data.get("venue", ""),
                }
                return content, f"doi:{doi}", meta
            except Exception:
                return f"DOI: {doi}", f"doi:{doi}", {}

        if "pdf_path" in params:
            from sciskills.utils.pdf_parser import parse_pdf
            backend = params.get("pdf_backend", "pymupdf")
            grobid_url = params.get("grobid_url", "http://localhost:8070")
            parsed = parse_pdf(params["pdf_path"], backend=backend, grobid_url=grobid_url)

            section_text = "\n\n".join(
                f"=== {s.heading} ===\n{s.content[:2000]}"
                for s in parsed.sections[:15]
            )
            content = f"Title: {parsed.title}\n\n{section_text}"
            meta = {"title": parsed.title}
            return content, f"pdf:{params['pdf_path']}", meta

        raise ValueError("Must provide one of: arxiv_id, doi, pdf_path")

    def _extract_structure(self, content: str, params: dict) -> dict:
        """Call LLM to extract structured fields from paper content."""
        llm = get_default_client()
        if "llm_model" in params:
            llm.model = params["llm_model"]

        # Truncate content to avoid token limits
        max_chars = 12000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[... truncated ...]"

        prompt = _EXTRACT_PROMPT.format(content=content)
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=3000,
        )

        # If we got raw text back (parse failed), try to salvage
        if "raw" in result and len(result) == 1:
            result = self._fallback_parse(result["raw"])

        return result

    def _fallback_parse(self, raw: str) -> dict:
        """Try to extract JSON from raw LLM output."""
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_extraction": raw}
