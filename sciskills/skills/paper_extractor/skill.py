"""
Skill 1: Paper Structural Extractor

Supports four extraction modes:
  metadata   — title, authors, year, venue, abstract only (no LLM for arXiv/DOI)
  method     — + research_question, methodology, datasets, baselines
  experiment — + metrics, main_findings, implementation_details
  full       — all fields including limitations, future_work

Every inferential field (research_question, problem_statement, methodology,
main_findings) carries confidence (0.0–1.0) and evidence (quoted sentences).

Output also includes _extraction_meta with mode, source, full_text_used, warnings.
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


# ── Mode definitions ──────────────────────────────────────────────────────── #

MODES = ("metadata", "method", "experiment", "full")

# Fields included per mode (cumulative)
_MODE_FIELDS: dict[str, list[str]] = {
    "metadata": ["title", "authors", "year", "venue", "abstract"],
    "method": ["research_question", "problem_statement", "methodology", "datasets", "baselines"],
    "experiment": ["metrics", "main_findings", "implementation_details"],
    "full": ["limitations", "future_work"],
}

def _fields_for_mode(mode: str) -> list[str]:
    """Return the cumulative set of fields to extract for a given mode."""
    order = ["metadata", "method", "experiment", "full"]
    fields: list[str] = []
    for m in order:
        fields.extend(_MODE_FIELDS[m])
        if m == mode:
            break
    return fields


# ── Per-mode LLM prompts ──────────────────────────────────────────────────── #

_SCHEMA_METADATA = """\
{
  "title": "string",
  "authors": ["string"],
  "year": "string or null",
  "venue": "string or null",
  "abstract": "string or null"
}"""

_SCHEMA_METHOD = """\
{
  "title": "string",
  "authors": ["string"],
  "year": "string or null",
  "venue": "string or null",
  "abstract": "string or null",
  "research_question": {
    "value": "the core research question or objective",
    "evidence": ["exact quoted sentence(s) from paper that state the question"],
    "confidence": 0.0
  },
  "problem_statement": {
    "value": "what problem is being solved",
    "evidence": ["exact quoted sentence(s)"],
    "confidence": 0.0
  },
  "methodology": {
    "approach": "high-level approach description",
    "model_architecture": "string or null",
    "key_techniques": ["string"],
    "novelty": "what is novel about this approach",
    "confidence": 0.0
  },
  "datasets": [
    {"name": "string", "version": "string or null", "scale": "string or null",
     "domain": "string or null", "public": true, "url": "string or null"}
  ],
  "baselines": [
    {"name": "string", "paper_ref": "string or null",
     "type": "prior_work or ablation or upper_bound"}
  ]
}"""

_SCHEMA_EXPERIMENT = """\
{
  "title": "string",
  "authors": ["string"],
  "year": "string or null",
  "venue": "string or null",
  "abstract": "string or null",
  "research_question": {"value": "string", "evidence": ["string"], "confidence": 0.0},
  "problem_statement": {"value": "string", "evidence": ["string"], "confidence": 0.0},
  "methodology": {
    "approach": "string", "model_architecture": "string or null",
    "key_techniques": ["string"], "novelty": "string", "confidence": 0.0
  },
  "datasets": [
    {"name": "string", "version": "string or null", "scale": "string or null",
     "domain": "string or null", "public": true, "url": "string or null"}
  ],
  "baselines": [
    {"name": "string", "paper_ref": "string or null",
     "type": "prior_work or ablation or upper_bound"}
  ],
  "metrics": [
    {"name": "string", "value": "string or null", "dataset": "string or null",
     "is_best": false, "evidence": "string or null"}
  ],
  "main_findings": [
    {"claim": "string", "evidence": ["exact quoted sentence(s)"], "confidence": 0.0}
  ],
  "implementation_details": {
    "code_available": true,
    "code_url": "string or null",
    "hardware": "string or null",
    "training_time": "string or null"
  }
}"""

_SCHEMA_FULL = """\
{
  "title": "string",
  "authors": ["string"],
  "year": "string or null",
  "venue": "string or null",
  "abstract": "string or null",
  "research_question": {"value": "string", "evidence": ["string"], "confidence": 0.0},
  "problem_statement": {"value": "string", "evidence": ["string"], "confidence": 0.0},
  "methodology": {
    "approach": "string", "model_architecture": "string or null",
    "key_techniques": ["string"], "novelty": "string", "confidence": 0.0
  },
  "datasets": [
    {"name": "string", "version": "string or null", "scale": "string or null",
     "domain": "string or null", "public": true, "url": "string or null"}
  ],
  "baselines": [
    {"name": "string", "paper_ref": "string or null",
     "type": "prior_work or ablation or upper_bound"}
  ],
  "metrics": [
    {"name": "string", "value": "string or null", "dataset": "string or null",
     "is_best": false, "evidence": "string or null"}
  ],
  "main_findings": [
    {"claim": "string", "evidence": ["exact quoted sentence(s)"], "confidence": 0.0}
  ],
  "implementation_details": {
    "code_available": true,
    "code_url": "string or null",
    "hardware": "string or null",
    "training_time": "string or null"
  },
  "limitations": ["string"],
  "future_work": ["string"]
}"""

_SCHEMAS = {
    "metadata": _SCHEMA_METADATA,
    "method": _SCHEMA_METHOD,
    "experiment": _SCHEMA_EXPERIMENT,
    "full": _SCHEMA_FULL,
}

_CONFIDENCE_GUIDE = """\
Confidence guidelines:
- 0.9–1.0: field value is directly stated verbatim in the text
- 0.7–0.9: clearly implied; high-confidence paraphrase
- 0.5–0.7: inferred from context; reasonable but not explicit
- < 0.5: uncertain guess; mark accordingly"""

_EXTRACT_PROMPT = """\
You are a scientific paper analysis assistant.
Extract structured information from the paper content below.
Return ONLY valid JSON matching the schema exactly. No markdown, no explanation.

{confidence_guide}

Schema:
{schema}

Rules:
- Use null for any field you cannot determine.
- evidence fields: copy SHORT exact quotes (≤ 2 sentences) from the paper text.
- confidence: follow the guidelines above. Use lower values for abstract-only content.
- For metrics, one entry per (metric, dataset) pair.
- is_best: true only if paper explicitly claims SOTA or best on that metric+dataset.
- baseline type: "prior_work" (another paper), "ablation" (component removed), "upper_bound" (oracle).

Paper content:
---
{content}
---"""


# ── Skill ─────────────────────────────────────────────────────────────────── #

@registry.register
class PaperStructuralExtractor(BaseSkill):
    name = "paper_structural_extractor"
    description = (
        "Extract structured information from an academic paper "
        "(arXiv ID, DOI, or PDF path). "
        "Supports four modes: metadata (fast, no LLM for API sources), "
        "method, experiment, full. "
        "Inferential fields include confidence scores and evidence quotes."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "arxiv_id": {"type": "string", "description": "arXiv ID, e.g. '2303.08774'"},
            "doi": {"type": "string", "description": "DOI, e.g. '10.1145/3292500.3330919'"},
            "pdf_path": {"type": "string", "description": "Local path to a PDF file"},
            "mode": {
                "type": "string",
                "enum": list(MODES),
                "default": "full",
                "description": (
                    "Extraction depth: "
                    "'metadata' (title/authors/year/venue only, fastest), "
                    "'method' (+methodology/datasets/baselines), "
                    "'experiment' (+metrics/findings/impl), "
                    "'full' (all fields incl. limitations/future_work)"
                ),
            },
            "pdf_backend": {
                "type": "string",
                "enum": ["pymupdf", "grobid"],
                "default": "pymupdf",
            },
            "grobid_url": {
                "type": "string",
                "default": "http://localhost:8070",
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
        "description": "Structured paper fields plus _extraction_meta",
    }

    def execute(self, params: dict) -> SkillResult:
        mode = params.get("mode", "full")
        if mode not in MODES:
            return SkillResult.fail(errors=[f"Invalid mode '{mode}'. Choose from: {MODES}"])

        warnings: list[str] = []
        try:
            content, source, meta, full_text_used = self._fetch_content(params, mode, warnings)
            structured = self._extract(content, mode, meta, warnings)

            # Attach IDs back
            structured["arxiv_id"] = (
                params["arxiv_id"].replace("arxiv:", "").strip()
                if "arxiv_id" in params else None
            )
            structured["doi"] = params.get("doi")

            structured["_extraction_meta"] = {
                "mode": mode,
                "source": source,
                "full_text_used": full_text_used,
                "warnings": warnings,
            }

            return SkillResult.ok(
                data=structured,
                metadata={"mode": mode, "source": source, "content_length": len(content)},
            )
        except Exception as e:
            return SkillResult.fail(errors=[str(e)])

    # ── Fetch ─────────────────────────────────────────────────────────────── #

    def _fetch_content(
        self, params: dict, mode: str, warnings: list[str]
    ) -> tuple[str, str, dict, bool]:
        """Return (text_content, source_label, api_meta, full_text_used)."""

        if "pdf_path" in params:
            return self._fetch_pdf(params, warnings)

        if "arxiv_id" in params:
            return self._fetch_arxiv(params, mode, warnings)

        if "doi" in params:
            return self._fetch_doi(params, mode, warnings)

        raise ValueError("Must provide one of: arxiv_id, doi, pdf_path")

    def _fetch_pdf(
        self, params: dict, warnings: list[str]
    ) -> tuple[str, str, dict, bool]:
        from sciskills.utils.pdf_parser import parse_pdf
        backend = params.get("pdf_backend", "pymupdf")
        grobid_url = params.get("grobid_url", "http://localhost:8070")
        parsed = parse_pdf(params["pdf_path"], backend=backend, grobid_url=grobid_url)

        section_text = "\n\n".join(
            f"=== {s.heading} ===\n{s.content[:2500]}"
            for s in parsed.sections[:15]
        )
        content = f"Title: {parsed.title}\n\n{section_text}"
        if len(content) > 14000:
            content = content[:14000] + "\n[... truncated ...]"
            warnings.append("truncated: PDF was too long, truncated at 14,000 characters")

        meta = {"title": parsed.title}
        return content, f"pdf:{params['pdf_path']}", meta, True

    def _fetch_arxiv(
        self, params: dict, mode: str, warnings: list[str]
    ) -> tuple[str, str, dict, bool]:
        arxiv_id = params["arxiv_id"].replace("arxiv:", "").strip()
        client = ArxivClient()
        meta = client.get_paper(arxiv_id)

        try:
            s2 = SemanticScholarClient()
            s2_data = s2.get_by_arxiv(arxiv_id)
            meta.update({
                "venue": s2_data.get("venue", meta.get("venue", "")),
                "year": s2_data.get("year", meta.get("year", "")),
            })
        except Exception:
            pass

        abstract = meta.get("abstract", "")
        content = f"Title: {meta.get('title', '')}\n\nAbstract: {abstract}"

        full_text_used = False
        if not abstract:
            warnings.append("abstract_only: no abstract available, extraction quality will be low")
        else:
            warnings.append(
                "abstract_only: only abstract available for arXiv ID without PDF; "
                "inferential fields will have lower confidence"
            )

        return content, f"arxiv:{arxiv_id}", meta, full_text_used

    def _fetch_doi(
        self, params: dict, mode: str, warnings: list[str]
    ) -> tuple[str, str, dict, bool]:
        doi = params["doi"]
        try:
            s2 = SemanticScholarClient()
            data = s2.get_by_doi(doi)
            abstract = (data.get("tldr") or {}).get("text", "") or data.get("abstract", "")
            meta = {
                "title": data.get("title", ""),
                "authors": [a.get("name", "") for a in data.get("authors", [])],
                "year": data.get("year"),
                "venue": data.get("venue", ""),
            }
            content = f"Title: {meta['title']}\n\nAbstract: {abstract}"
            warnings.append(
                "abstract_only: only abstract available for DOI source; "
                "inferential fields will have lower confidence"
            )
            return content, f"doi:{doi}", meta, False
        except Exception:
            warnings.append(f"doi_fetch_failed: could not retrieve data for DOI {doi}")
            return f"DOI: {doi}", f"doi:{doi}", {}, False

    # ── Extract ───────────────────────────────────────────────────────────── #

    def _extract(
        self, content: str, mode: str, api_meta: dict, warnings: list[str]
    ) -> dict:
        """
        For metadata mode on API sources: skip LLM, build result from api_meta directly.
        For all other modes, call LLM with the mode-appropriate schema.
        """
        if mode == "metadata" and api_meta:
            return self._build_metadata_only(api_meta)

        schema = _SCHEMAS[mode]
        prompt = _EXTRACT_PROMPT.format(
            confidence_guide=_CONFIDENCE_GUIDE,
            schema=schema,
            content=content,
        )

        llm = get_default_client()
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=_max_tokens_for_mode(mode),
        )

        if "raw" in result and len(result) == 1:
            result = self._fallback_parse(result["raw"])
            warnings.append("llm_retry: JSON parsing failed, fell back to regex extraction")

        # Merge API metadata into top-level fields (API is more reliable for these)
        if api_meta:
            for field in ("title", "authors", "year", "venue"):
                if api_meta.get(field) and not result.get(field):
                    result[field] = api_meta[field]

        # Downgrade confidence on abstract-only sources
        is_abstract_only = any("abstract_only" in w for w in warnings)
        if is_abstract_only:
            result = _cap_confidence(result, cap=0.65)

        return result

    def _build_metadata_only(self, api_meta: dict) -> dict:
        """Build a metadata-mode result directly from API data without calling LLM."""
        return {
            "title": api_meta.get("title", ""),
            "authors": api_meta.get("authors", []),
            "year": str(api_meta.get("year", "")) if api_meta.get("year") else None,
            "venue": api_meta.get("venue", "") or None,
            "abstract": api_meta.get("abstract", "") or None,
        }

    def _fallback_parse(self, raw: str) -> dict:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_extraction": raw}


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _max_tokens_for_mode(mode: str) -> int:
    return {"metadata": 600, "method": 1500, "experiment": 2500, "full": 3500}.get(mode, 2500)


def _cap_confidence(obj: Any, cap: float) -> Any:
    """Recursively cap all 'confidence' float values in a nested dict/list."""
    if isinstance(obj, dict):
        return {
            k: (min(v, cap) if k == "confidence" and isinstance(v, (int, float)) else _cap_confidence(v, cap))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_cap_confidence(item, cap) for item in obj]
    return obj
