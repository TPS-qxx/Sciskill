"""
Skill 5: Research Gap Identifier

Inputs:
  - papers: list of structured paper dicts (output from Skill 1, or manual)
  - dimensions: list of analysis dimensions (default: ["methods", "datasets", "tasks"])
  - min_coverage_threshold: float (gaps exist when coverage < threshold, default 0.3)

Output:
  {
    "coverage_matrix": {...},
    "gaps": [...],
    "trend_analysis": "...",
    "suggested_directions": [...]
  }
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sciskills.core.base import BaseSkill, SkillResult
from sciskills.core.registry import registry
from sciskills.utils.llm_client import get_default_client


@registry.register
class ResearchGapIdentifier(BaseSkill):
    name = "research_gap_identifier"
    description = (
        "Analyze a collection of structured paper information to identify research gaps. "
        "Builds a coverage matrix across methods × datasets × tasks dimensions "
        "and uses LLM to suggest unexplored research directions."
        "Works best with outputs from the paper_structural_extractor skill."
    )
    input_schema = {
        "type": "object",
        "required": ["papers"],
        "properties": {
            "papers": {
                "type": "array",
                "description": (
                    "List of structured paper dicts. Each should have at minimum: "
                    "title, methodology (with approach and key_techniques), "
                    "datasets (list of {name}), metrics (list of {name})."
                ),
                "items": {"type": "object"},
            },
            "dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["methods", "datasets", "tasks"],
                "description": "Analysis dimensions for the coverage matrix.",
            },
            "min_coverage_threshold": {
                "type": "number",
                "default": 0.3,
                "description": "Fraction of papers covering a combination below which it's considered a gap.",
            },
            "topic": {
                "type": "string",
                "description": "Research topic/field for context (e.g. 'relation extraction', 'drug discovery').",
            },
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "coverage_matrix": {"type": "object"},
            "gaps": {"type": "array"},
            "trend_analysis": {"type": "string"},
            "suggested_directions": {"type": "array"},
        },
    }

    def execute(self, params: dict) -> SkillResult:
        papers: list[dict] = params["papers"]
        if not papers:
            return SkillResult.fail(errors=["No papers provided."])

        dimensions = params.get("dimensions", ["methods", "datasets", "tasks"])
        threshold = params.get("min_coverage_threshold", 0.3)
        topic = params.get("topic", "")

        # 1. Extract dimension values from papers
        methods = self._extract_methods(papers)
        datasets = self._extract_datasets(papers)
        tasks = self._extract_tasks(papers)

        # 2. Build coverage matrices
        coverage = {}
        gaps = []

        if "methods" in dimensions and "datasets" in dimensions:
            md_matrix, md_gaps = self._build_matrix(papers, methods, datasets, "methods", "datasets", threshold)
            coverage["methods_x_datasets"] = md_matrix
            gaps.extend(md_gaps)

        if "methods" in dimensions and "tasks" in dimensions and tasks:
            mt_matrix, mt_gaps = self._build_matrix(papers, methods, tasks, "methods", "tasks", threshold)
            coverage["methods_x_tasks"] = mt_matrix
            gaps.extend(mt_gaps)

        if "datasets" in dimensions and "tasks" in dimensions and tasks:
            dt_matrix, dt_gaps = self._build_matrix(papers, datasets, tasks, "datasets", "tasks", threshold)
            coverage["datasets_x_tasks"] = dt_matrix
            gaps.extend(dt_gaps)

        # 3. Deduplicate gaps
        seen_gaps: set[str] = set()
        unique_gaps = []
        for g in gaps:
            key = g["description"]
            if key not in seen_gaps:
                seen_gaps.add(key)
                unique_gaps.append(g)

        # 4. LLM analysis
        trend_analysis, suggested_directions = self._llm_analysis(
            papers, unique_gaps, methods, datasets, tasks, topic
        )

        return SkillResult.ok(
            data={
                "coverage_matrix": coverage,
                "gaps": unique_gaps,
                "trend_analysis": trend_analysis,
                "suggested_directions": suggested_directions,
                "summary": {
                    "num_papers": len(papers),
                    "unique_methods": len(methods),
                    "unique_datasets": len(datasets),
                    "unique_tasks": len(tasks),
                    "gaps_identified": len(unique_gaps),
                },
            }
        )

    # ------------------------------------------------------------------ #

    def _extract_methods(self, papers: list[dict]) -> list[str]:
        methods: set[str] = set()
        for p in papers:
            meth = p.get("methodology", {})
            if isinstance(meth, dict):
                approach = meth.get("approach", "")
                if approach:
                    methods.add(approach.strip())
                for t in meth.get("key_techniques", []):
                    if t:
                        methods.add(t.strip())
            # Fallback: check top-level 'approach' field
            if p.get("approach"):
                methods.add(p["approach"].strip())
        return sorted(methods - {""})

    def _extract_datasets(self, papers: list[dict]) -> list[str]:
        datasets: set[str] = set()
        for p in papers:
            for d in p.get("datasets", []):
                if isinstance(d, dict):
                    name = d.get("name", "")
                elif isinstance(d, str):
                    name = d
                else:
                    continue
                if name:
                    datasets.add(name.strip())
        return sorted(datasets - {""})

    def _extract_tasks(self, papers: list[dict]) -> list[str]:
        tasks: set[str] = set()
        for p in papers:
            # Try metrics names as proxy for task
            for m in p.get("metrics", []):
                if isinstance(m, dict):
                    name = m.get("name", "")
                    if name:
                        tasks.add(name.strip())
            # Try explicit task field
            if p.get("task"):
                tasks.add(str(p["task"]).strip())
            # Try venue/area
            rq = p.get("research_question", "")
            if rq and len(rq) < 60:
                tasks.add(rq.strip())
        return sorted(tasks - {""})[:20]  # cap to prevent explosion

    def _build_matrix(
        self,
        papers: list[dict],
        rows: list[str],
        cols: list[str],
        row_key: str,
        col_key: str,
        threshold: float,
    ) -> tuple[dict, list[dict]]:
        """
        Build a coverage matrix (rows × cols) showing fraction of papers covering each pair.
        Return (matrix_dict, gaps_list).
        """
        if not rows or not cols:
            return {}, []

        # count[row][col] = number of papers covering (row, col)
        count: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for paper in papers:
            paper_methods = set(self._extract_methods([paper]))
            paper_datasets = set(self._extract_datasets([paper]))
            paper_tasks = set(self._extract_tasks([paper]))

            dim_map = {
                "methods": paper_methods,
                "datasets": paper_datasets,
                "tasks": paper_tasks,
            }

            row_set = dim_map.get(row_key, set())
            col_set = dim_map.get(col_key, set())

            for r in rows:
                if any(r.lower() in s.lower() or s.lower() in r.lower() for s in row_set):
                    for c in cols:
                        if any(c.lower() in s.lower() or s.lower() in c.lower() for s in col_set):
                            count[r][c] += 1

        n = len(papers)
        matrix = {
            "row_axis": row_key,
            "col_axis": col_key,
            "rows": rows,
            "cols": cols,
            "coverage": {
                r: {c: round(count[r][c] / n, 3) for c in cols}
                for r in rows
            },
        }

        gaps = []
        for r in rows:
            for c in cols:
                frac = count[r][c] / n
                if frac < threshold:
                    confidence = 1.0 - frac
                    gaps.append({
                        "description": f"{r} has not been evaluated on {c}",
                        "row_dimension": row_key,
                        "col_dimension": col_key,
                        "row_value": r,
                        "col_value": c,
                        "coverage_fraction": round(frac, 3),
                        "confidence": round(confidence, 2),
                    })

        # Sort by confidence
        gaps.sort(key=lambda g: g["confidence"], reverse=True)
        return matrix, gaps

    def _llm_analysis(
        self,
        papers: list[dict],
        gaps: list[dict],
        methods: list[str],
        datasets: list[str],
        tasks: list[str],
        topic: str,
    ) -> tuple[str, list[str]]:
        """Use LLM to generate trend analysis and concrete research direction suggestions."""

        paper_summaries = "\n".join(
            f"- {p.get('title', 'Untitled')} ({p.get('year', '?')}): "
            f"method={p.get('methodology', {}).get('approach', '?') if isinstance(p.get('methodology'), dict) else '?'}"
            for p in papers[:15]
        )

        top_gaps = "\n".join(
            f"- {g['description']} (confidence: {g['confidence']})"
            for g in gaps[:10]
        )

        prompt = f"""You are a senior researcher helping identify research gaps{f' in {topic}' if topic else ''}.

Papers analyzed ({len(papers)} total):
{paper_summaries}

Methods in the literature: {', '.join(methods[:10])}
Datasets used: {', '.join(datasets[:10])}
Identified gaps (low coverage combinations):
{top_gaps if top_gaps else 'None identified by coverage analysis'}

Tasks:
1. Write a 2-3 sentence trend analysis of the current research landscape.
2. List 3-5 concrete, actionable research directions that address the identified gaps.

Respond with JSON in this exact format:
{{
  "trend_analysis": "...",
  "suggested_directions": [
    {{"direction": "...", "rationale": "...", "feasibility": "high|medium|low"}},
    ...
  ]
}}"""

        try:
            llm = get_default_client()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=800,
            )
            trend = result.get("trend_analysis", "")
            directions = [d.get("direction", "") for d in result.get("suggested_directions", [])]
            return trend, [d for d in directions if d]
        except Exception as e:
            return f"[Analysis unavailable: {e}]", []
