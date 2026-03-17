---
name: research-gap-identifier
description: Analyze a collection of structured paper information to identify research gaps and suggest unexplored directions. Use after extracting multiple papers with paper-structural-extractor, when the user wants to understand what has not been studied, which method-dataset combinations are missing, or what to work on next. Best suited for literature surveys with 5+ papers.
---

# Research Gap Identifier

Analyzes structured paper data to build a coverage matrix across methods × datasets × tasks dimensions, identifies under-explored combinations, and uses an LLM to suggest concrete research directions.

## When to Use

- User has structured data for 5+ papers (ideally from `paper-structural-extractor`)
- User wants to understand what has not been studied in a field
- User is writing a Related Work section and needs to characterize the literature landscape
- User is brainstorming PhD/research project ideas

## Workflow

### Option A: Automated (recommended)

Use `paper-structural-extractor` first to collect paper data, then pipe into this skill:

```bash
# Step 1: Extract papers one by one (or use a loop)
python skills/paper-structural-extractor/run.py --arxiv 2303.08774 > /tmp/paper1.json
python skills/paper-structural-extractor/run.py --arxiv 2110.07602 > /tmp/paper2.json
# ... repeat for each paper

# Step 2: Combine into a papers array
python skills/research-gap-identifier/merge_papers.py /tmp/paper1.json /tmp/paper2.json ... > /tmp/papers.json

# Step 3: Run gap analysis
python skills/research-gap-identifier/run.py --input /tmp/papers.json --topic "named entity recognition"
```

### Option B: Manual structured input

If you already have paper metadata, create `/tmp/papers.json` in this format:

```json
{
  "papers": [
    {
      "title": "BERT for NER",
      "year": "2019",
      "methodology": {
        "approach": "BERT fine-tuning",
        "key_techniques": ["BERT", "CRF layer"]
      },
      "datasets": [
        {"name": "CoNLL-2003"},
        {"name": "OntoNotes 5.0"}
      ],
      "metrics": [{"name": "F1"}]
    },
    ...
  ],
  "topic": "Named Entity Recognition",
  "min_coverage_threshold": 0.3
}
```

Then run:
```bash
python skills/research-gap-identifier/run.py --input /tmp/papers.json
```

## Step-by-Step Instructions

1. **Collect structured paper data** (at least 5 papers for meaningful analysis).

2. **Run the gap analysis script** (see Workflow above).

3. **Interpret the coverage matrix**:
   - Each cell shows the fraction of papers that use a particular method on a particular dataset.
   - Cells with value 0.0 are unexplored combinations.
   - Cells below the `min_coverage_threshold` (default 0.3) are flagged as gaps.

4. **Review the gaps list** (`gaps` field in output):
   - Gaps are sorted by `confidence` (higher = less explored).
   - Present the top 5-10 gaps to the user.

5. **Present the suggested directions** (`suggested_directions`):
   - These are LLM-generated, concrete research proposals.
   - Discuss their feasibility and novelty with the user.

6. **For the Related Work section**: use `trend_analysis` as a starting paragraph describing the research landscape.

## Output Fields

```
coverage_matrix   — methods×datasets, methods×tasks, datasets×tasks coverage fractions
gaps              — sorted list of under-explored combinations with confidence scores
trend_analysis    — 2-3 sentence description of the research landscape
suggested_directions — 3-5 concrete, actionable research directions
summary           — counts (papers analyzed, unique methods/datasets/tasks, gaps found)
```

## Tips

- The more papers you include, the more reliable the coverage matrix. Aim for 10-20 papers minimum.
- Set `min_coverage_threshold` higher (e.g. 0.5) for stricter gap detection.
- The analysis is only as good as the paper extraction. Verify that datasets and methods are correctly extracted before running.
- Gaps are structural (what hasn't been done) not necessarily meaningful (worthwhile to do). Use the LLM suggestions to filter.
