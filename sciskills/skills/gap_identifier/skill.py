"""
Skill 5: Research Gap Identifier

Identifies typed research gaps from a set of structured paper extractions.

Gap types:
  task_gap       — method not applied to this task
  data_gap       — no benchmark for this domain/condition
  method_gap     — no approach addresses a known challenge
  evaluation_gap — claim made but no metric captures it
  deployment_gap — lab results, not tested in production
  theoretical_gap — empirical results with no theoretical basis

Each gap carries: gap_type, description, supporting_papers (with evidence quotes),
missing_combination, confidence, actionable_direction.
"""
from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.utils.llm_client import get_default_client

GAP_TYPES = [
    "task_gap",
    "data_gap",
    "method_gap",
    "evaluation_gap",
    "deployment_gap",
    "theoretical_gap",
]

MIN_PAPERS_WARN = 5
MIN_PAPERS_MODERATE = 15
MIN_PAPERS_STRONG = 30


@registry.register
class ResearchGapIdentifier(BaseSkill):
    name = "research_gap_identifier"
    description = (
        "Analyze structured paper extractions to identify typed research gaps "
        "(task_gap, data_gap, method_gap, evaluation_gap, deployment_gap, theoretical_gap). "
        "Builds a coverage matrix and generates evidence-backed gap objects with confidence scores. "
        "Requires 5+ papers; works best with paper_structural_extractor full-mode output."
    )
    input_schema = {
        "type": "object",
        "required": ["papers", "topic"],
        "properties": {
            "papers": {
                "type": "array",
                "description": (
                    "List of structured paper dicts. Best when from paper_structural_extractor "
                    "with mode='full'. Minimum 5 papers required."
                ),
                "items": {"type": "object"},
                "minItems": 1,
            },
            "topic": {
                "type": "string",
                "description": "The research field/task being analyzed (e.g. 'named entity recognition').",
            },
            "gap_types": {
                "type": "array",
                "items": {"type": "string", "enum": GAP_TYPES},
                "description": "Gap types to detect. Default: all types.",
            },
            "min_coverage_threshold": {
                "type": "number",
                "default": 0.3,
                "description": "Coverage fraction below which a combination is flagged as a gap.",
            },
            "max_gaps": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of gaps to return, sorted by confidence.",
            },
            "include_directions": {
                "type": "boolean",
                "default": True,
                "description": "Generate LLM research direction suggestions.",
            },
            "include_matrix": {
                "type": "boolean",
                "default": True,
                "description": "Include the full coverage matrix in output.",
            },
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "object"},
            "gaps": {"type": "array"},
            "coverage_matrix": {"type": "object"},
            "trend_analysis": {"type": "string"},
            "suggested_directions": {"type": "array"},
            "warnings": {"type": "array"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        papers: list[dict] = params["papers"]
        topic: str = params.get("topic", "")
        threshold = params.get("min_coverage_threshold", 0.3)
        max_gaps = params.get("max_gaps", 10)
        include_directions = params.get("include_directions", True)
        include_matrix = params.get("include_matrix", True)
        requested_gap_types = set(params.get("gap_types") or GAP_TYPES)
        process_warnings: list[str] = []

        # Minimum paper threshold enforcement
        if len(papers) < MIN_PAPERS_WARN:
            return SkillResult.fail(
                errors=[
                    f"Only {len(papers)} paper(s) provided. "
                    f"Research gap analysis requires at least {MIN_PAPERS_WARN} papers. "
                    "Please extract more papers with paper-structural-extractor first."
                ]
            )
        if len(papers) < MIN_PAPERS_MODERATE:
            process_warnings.append(
                f"Only {len(papers)} papers: treat results as exploratory (preliminary). "
                "Recommend 15+ papers for moderate confidence."
            )
        elif len(papers) < MIN_PAPERS_STRONG:
            process_warnings.append(
                f"{len(papers)} papers: moderate confidence. "
                "30+ papers recommended for strong claims."
            )

        confidence_level = (
            "strong" if len(papers) >= MIN_PAPERS_STRONG
            else "moderate" if len(papers) >= MIN_PAPERS_MODERATE
            else "exploratory"
        )

        # Extract dimensions
        methods = self._extract_methods(papers)
        datasets = self._extract_datasets(papers)
        tasks = self._extract_tasks(papers)

        # Build coverage matrices
        coverage: dict[str, Any] = {}
        structural_gaps: list[dict] = []

        if methods and datasets:
            md_matrix, md_gaps = self._build_matrix(papers, methods, datasets, "methods", "datasets", threshold)
            coverage["methods_x_datasets"] = md_matrix
            structural_gaps.extend(md_gaps)

        if methods and tasks:
            mt_matrix, mt_gaps = self._build_matrix(papers, methods, tasks, "methods", "tasks", threshold)
            coverage["methods_x_tasks"] = mt_matrix
            structural_gaps.extend(mt_gaps)

        zero_coverage_pairs = [
            [g["missing_combination"].get("method", ""), g["missing_combination"].get("dataset", "")]
            for g in structural_gaps
            if g.get("confidence", 0) == 1.0
        ]
        coverage["zero_coverage_pairs"] = zero_coverage_pairs[:20]

        # Assign gap types to structural gaps
        typed_gaps = self._assign_gap_types(structural_gaps, papers, requested_gap_types)

        # Add supporting papers with evidence to each gap
        enriched_gaps = self._enrich_gaps_with_evidence(typed_gaps, papers)

        # Sort by confidence and cap
        enriched_gaps.sort(key=lambda g: g["confidence"], reverse=True)
        final_gaps = enriched_gaps[:max_gaps]

        # LLM analysis
        trend_analysis = ""
        suggested_directions: list[dict] = []
        if include_directions:
            trend_analysis, suggested_directions = self._llm_analysis(
                papers, final_gaps, methods, datasets, tasks, topic
            )

        return SkillResult.ok(
            data={
                "summary": {
                    "papers_analyzed": len(papers),
                    "unique_methods": len(methods),
                    "unique_datasets": len(datasets),
                    "unique_tasks": len(tasks),
                    "gaps_found": len(final_gaps),
                    "confidence_level": confidence_level,
                    "coverage_warning": process_warnings[0] if process_warnings else None,
                },
                "gaps": final_gaps,
                "coverage_matrix": coverage if include_matrix else {},
                "trend_analysis": trend_analysis,
                "suggested_directions": suggested_directions,
                "warnings": process_warnings,
            }
        )

    # ─── Extraction helpers ──────────────────────────────────────────────── #

    def _extract_methods(self, papers: list[dict]) -> list[str]:
        methods: set[str] = set()
        for p in papers:
            meth = p.get("methodology", {})
            if isinstance(meth, dict):
                approach = meth.get("approach", "")
                if approach and len(approach) < 80:
                    methods.add(approach.strip())
                for t in meth.get("key_techniques", []):
                    if t and len(t) < 60:
                        methods.add(t.strip())
            elif isinstance(meth, str) and meth:
                methods.add(meth.strip())
        return sorted(m for m in methods if m)

    def _extract_datasets(self, papers: list[dict]) -> list[str]:
        datasets: set[str] = set()
        for p in papers:
            for d in p.get("datasets", []):
                name = d.get("name", "") if isinstance(d, dict) else str(d)
                if name:
                    datasets.add(name.strip())
        return sorted(d for d in datasets if d)

    def _extract_tasks(self, papers: list[dict]) -> list[str]:
        tasks: set[str] = set()
        for p in papers:
            for m in p.get("metrics", []):
                name = m.get("name", "") if isinstance(m, dict) else str(m)
                if name and len(name) < 40:
                    tasks.add(name.strip())
            if p.get("task"):
                tasks.add(str(p["task"]).strip())
            rq = p.get("research_question", {})
            if isinstance(rq, dict):
                rq = rq.get("value", "")
            if rq and len(rq) < 60:
                tasks.add(rq.strip())
        return sorted(t for t in tasks if t)[:20]

    # ─── Coverage matrix ─────────────────────────────────────────────────── #

    def _build_matrix(
        self,
        papers: list[dict],
        rows: list[str],
        cols: list[str],
        row_key: str,
        col_key: str,
        threshold: float,
    ) -> tuple[dict, list[dict]]:
        if not rows or not cols:
            return {}, []

        count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        n = len(papers)

        for paper in papers:
            paper_methods = set(self._extract_methods([paper]))
            paper_datasets = set(self._extract_datasets([paper]))
            paper_tasks = set(self._extract_tasks([paper]))
            dim_map = {"methods": paper_methods, "datasets": paper_datasets, "tasks": paper_tasks}

            row_set = dim_map.get(row_key, set())
            col_set = dim_map.get(col_key, set())

            for r in rows:
                if any(r.lower() in s.lower() or s.lower() in r.lower() for s in row_set):
                    for c in cols:
                        if any(c.lower() in s.lower() or s.lower() in c.lower() for s in col_set):
                            count[r][c] += 1

        matrix = {
            "row_axis": row_key,
            "col_axis": col_key,
            "rows": rows[:15],
            "cols": cols[:15],
            "coverage": {
                r: {c: round(count[r][c] / n, 3) for c in cols[:15]}
                for r in rows[:15]
            },
        }

        gaps = []
        gap_counter = [0]
        for r in rows[:15]:
            for c in cols[:15]:
                frac = count[r][c] / n
                if frac < threshold:
                    gap_counter[0] += 1
                    gaps.append({
                        "gap_id": f"gap_{gap_counter[0]:03d}",
                        "gap_type": "task_gap",  # default; overridden by _assign_gap_types
                        "description": f"{r} has not been evaluated on {c}",
                        "supporting_papers": [],
                        "missing_combination": {
                            "method": r if row_key == "methods" else None,
                            "dataset": c if col_key == "datasets" else (r if row_key == "datasets" else None),
                            "task": c if col_key == "tasks" else (r if row_key == "tasks" else None),
                        },
                        "coverage_fraction": round(frac, 3),
                        "confidence": round(1.0 - frac, 2),
                        "actionable_direction": "",
                    })

        gaps.sort(key=lambda g: g["confidence"], reverse=True)
        return matrix, gaps

    # ─── Gap type assignment ─────────────────────────────────────────────── #

    def _assign_gap_types(
        self, gaps: list[dict], papers: list[dict], requested_types: set[str]
    ) -> list[dict]:
        """Heuristically assign gap_type based on the missing combination dimensions."""
        result = []
        for g in gaps:
            mc = g.get("missing_combination", {})
            has_method = bool(mc.get("method"))
            has_dataset = bool(mc.get("dataset"))
            has_task = bool(mc.get("task"))

            if has_method and has_dataset and not has_task:
                gap_type = "data_gap"  # method exists but no dataset for it
            elif has_method and has_task and not has_dataset:
                gap_type = "task_gap"  # method not applied to this task
            elif has_dataset and has_task and not has_method:
                gap_type = "method_gap"  # no method for this dataset+task
            elif has_method and not has_dataset:
                gap_type = "evaluation_gap"  # method not evaluated
            else:
                gap_type = "task_gap"

            if gap_type not in requested_types:
                continue

            g = dict(g)
            g["gap_type"] = gap_type
            result.append(g)
        return result

    # ─── Evidence enrichment ─────────────────────────────────────────────── #

    def _enrich_gaps_with_evidence(
        self, gaps: list[dict], papers: list[dict]
    ) -> list[dict]:
        """
        For each gap, find papers that mention the gap's dimensions in limitations or future_work,
        and add them as supporting_papers with evidence quotes.
        """
        for gap in gaps:
            mc = gap.get("missing_combination", {})
            keywords = [v for v in mc.values() if v]
            if not keywords:
                continue

            supporting = []
            for paper in papers:
                evidence_quotes = []
                # Check limitations
                for lim in paper.get("limitations", []):
                    if any(kw.lower() in lim.lower() for kw in keywords):
                        evidence_quotes.append(lim)
                # Check future_work
                for fw in paper.get("future_work", []):
                    if any(kw.lower() in fw.lower() for kw in keywords):
                        evidence_quotes.append(fw)

                if evidence_quotes:
                    supporting.append({
                        "title": paper.get("title", "Unknown"),
                        "year": paper.get("year"),
                        "evidence": evidence_quotes[0],
                    })

            gap["supporting_papers"] = supporting[:3]
        return gaps

    # ─── LLM analysis ────────────────────────────────────────────────────── #

    def _llm_analysis(
        self,
        papers: list[dict],
        gaps: list[dict],
        methods: list[str],
        datasets: list[str],
        tasks: list[str],
        topic: str,
    ) -> tuple[str, list[dict]]:
        paper_summaries = "\n".join(
            f"- {p.get('title', 'Untitled')} ({p.get('year', '?')}): "
            f"method={p.get('methodology', {}).get('approach', '?') if isinstance(p.get('methodology'), dict) else '?'}"
            for p in papers[:15]
        )
        top_gaps_text = "\n".join(
            f"- [{g['gap_type']}] {g['description']} (confidence: {g['confidence']})"
            for g in gaps[:8]
        )

        prompt = f"""You are a senior researcher identifying research gaps in: {topic or 'the given field'}.

Papers analyzed ({len(papers)} total):
{paper_summaries}

Key methods: {', '.join(methods[:8])}
Key datasets: {', '.join(datasets[:8])}

Identified coverage gaps:
{top_gaps_text if top_gaps_text else 'None identified by coverage analysis'}

Tasks:
1. Write a 2-3 sentence trend_analysis: dominant approaches, temporal shifts, converging paradigms.
2. Suggest 3-5 concrete research directions that address the identified gaps.

Respond with JSON only, no markdown:
{{
  "trend_analysis": "...",
  "suggested_directions": [
    {{
      "title": "short name",
      "rationale": "why this is promising",
      "gap_ids": ["gap_001"],
      "feasibility": "high|medium|low",
      "novelty": "high|medium|low"
    }}
  ]
}}"""

        try:
            llm = get_default_client()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=900,
            )
            trend = result.get("trend_analysis", "")
            directions = result.get("suggested_directions", [])
            return trend, [d for d in directions if isinstance(d, dict)]
        except Exception as e:
            return f"[Trend analysis unavailable: {e}]", []
