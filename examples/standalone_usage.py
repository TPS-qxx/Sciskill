"""
Standalone usage examples for all SciSkills skills.

Prerequisites:
    pip install sciskills
    export LLM_API_KEY=your_key
    export LLM_BASE_URL=https://ep-llm.zhenguanyu.com/gateway-cn-online/openai-compatible/v1
    export LLM_MODEL=doubao-seed-1.8
"""
import os
import json

# ── Set up LLM config before importing ─────────────────────────────
os.environ.setdefault("LLM_API_KEY", "ZMaXcj5QE25D5oUA")
os.environ.setdefault(
    "LLM_BASE_URL",
    "https://ep-llm.zhenguanyu.com/gateway-cn-online/openai-compatible/v1",
)
os.environ.setdefault("LLM_MODEL", "doubao-seed-1.8")

import sciskills
from sciskills import registry


def print_result(title: str, result) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if result.success:
        print(json.dumps(result.data, indent=2, ensure_ascii=False)[:2000])
    else:
        print(f"FAILED: {result.errors}")
    print(f"  [elapsed: {result.metadata.get('elapsed_seconds', '?')}s]")


# ── Skill 1: Paper Structural Extractor ────────────────────────────
def demo_paper_extractor():
    skill = registry.get("paper_structural_extractor")
    result = skill({"arxiv_id": "1706.03762"})  # Attention Is All You Need
    print_result("Skill 1: Paper Structural Extractor", result)
    return result


# ── Skill 2: BibTeX Fixer & Enricher ───────────────────────────────
def demo_bibtex_fixer():
    sample_bib = """
@article{vaswani2017,
  title = {Attention Is All You Need},
  author = {Ashish Vaswani and Noam Shazeer},
  year = {2017},
  doi = {10.48550/arXiv.1706.03762}
}
@article{devlin_bert,
  title = {{BERT}: Pre-training},
  author = {JACOB DEVLIN and Ming-Wei Chang},
  booktitle = {NAACL}
}
"""
    skill = registry.get("bibtex_fixer_enricher")
    result = skill({
        "bibtex_str": sample_bib,
        "auto_enrich": False,
        "remove_duplicates": True,
        "normalize_authors": True,
    })
    print_result("Skill 2: BibTeX Fixer & Enricher", result)


# ── Skill 3: Experiment Result Comparator ──────────────────────────
def demo_experiment_comparator():
    experiments = [
        {"name": "BERT-base",    "metrics": {"F1": 88.5, "Precision": 87.2, "Latency_ms": 120}},
        {"name": "RoBERTa-large","metrics": {"F1": 91.2, "Precision": 90.8, "Latency_ms": 280}},
        {"name": "DistilBERT",   "metrics": {"F1": 85.3, "Precision": 84.1, "Latency_ms": 65}},
        {"name": "XLNet",        "metrics": {"F1": 90.1, "Precision": 89.5, "Latency_ms": 310}},
    ]
    skill = registry.get("experiment_result_comparator")
    result = skill({
        "experiments": experiments,
        "primary_metric": "F1",
        "higher_is_better": {"F1": True, "Precision": True, "Latency_ms": False},
        "output_format": "all",
        "caption": "NER results on CoNLL-2003 test set.",
        "label": "tab:ner_results",
        "include_tradeoff": True,
    })
    print_result("Skill 3: Experiment Result Comparator", result)
    if result.success:
        print("\n--- LaTeX Table ---")
        print(result.data["latex_table"])
        print("\n--- Markdown Table ---")
        print(result.data["markdown_table"])


# ── Skill 4: Statistical Test Advisor ──────────────────────────────
def demo_statistical_advisor():
    import numpy as np
    rng = np.random.default_rng(42)
    control = rng.normal(50, 10, 35).tolist()
    treatment = rng.normal(58, 10, 32).tolist()

    skill = registry.get("statistical_test_advisor")
    result = skill({
        "research_question_type": "group_comparison",
        "num_groups": 2,
        "variable_type": "continuous",
        "paired": False,
        "sample_size": [35, 32],
        "data": [control, treatment],
        "alpha": 0.05,
        "context": "Comparing exam scores between control and treatment groups in an educational intervention study.",
    })
    print_result("Skill 4: Statistical Test Advisor", result)
    if result.success:
        print("\n--- Python Code ---")
        print(result.data["python_code"])


# ── Skill 5: Research Gap Identifier ───────────────────────────────
def demo_gap_identifier():
    # Simulated structured paper data (normally from Skill 1)
    papers = [
        {
            "title": "BERT for NER",
            "year": "2019",
            "methodology": {"approach": "BERT fine-tuning", "key_techniques": ["BERT", "CRF"]},
            "datasets": [{"name": "CoNLL-2003"}, {"name": "OntoNotes"}],
            "metrics": [{"name": "F1"}],
        },
        {
            "title": "RoBERTa for Text Classification",
            "year": "2020",
            "methodology": {"approach": "RoBERTa fine-tuning", "key_techniques": ["RoBERTa"]},
            "datasets": [{"name": "SST-2"}, {"name": "MNLI"}],
            "metrics": [{"name": "Accuracy"}],
        },
        {
            "title": "GPT for Few-Shot NER",
            "year": "2022",
            "methodology": {"approach": "GPT prompting", "key_techniques": ["GPT-3", "few-shot"]},
            "datasets": [{"name": "CoNLL-2003"}],
            "metrics": [{"name": "F1"}],
        },
    ]
    skill = registry.get("research_gap_identifier")
    result = skill({
        "papers": papers,
        "topic": "Named Entity Recognition with pre-trained language models",
    })
    print_result("Skill 5: Research Gap Identifier", result)


# ── Skill 6: Reproducibility Checker ───────────────────────────────
def demo_reproducibility_checker():
    # Point to a local repo path or use a GitHub URL
    # For demo, we use a local temp directory
    import tempfile
    from pathlib import Path

    tmp = tempfile.mkdtemp()
    repo = Path(tmp)
    (repo / "requirements.txt").write_text("torch>=2.0\nnumpy>=1.24\n")
    (repo / "README.md").write_text(
        "# MyModel\n\n## Installation\npip install -r requirements.txt\n\n## Usage\npython train.py --seed 42\n"
    )
    (repo / "train.py").write_text(
        "import torch, random, numpy as np\n"
        "torch.manual_seed(42)\nnp.random.seed(42)\nrandom.seed(42)\n"
        "# Training code here\n"
    )
    (repo / "LICENSE").write_text("MIT License\n")

    skill = registry.get("reproducibility_checker")
    result = skill({"local_path": str(repo)})
    print_result("Skill 6: Reproducibility Checker", result)
    if result.success:
        print(f"\nScore: {result.data['score']}/100")
        for check in result.data["checks"]:
            status = "✓" if check["passed"] else "✗"
            print(f"  {status} {check['item']}")


# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    demos = {
        "1": demo_paper_extractor,
        "2": demo_bibtex_fixer,
        "3": demo_experiment_comparator,
        "4": demo_statistical_advisor,
        "5": demo_gap_identifier,
        "6": demo_reproducibility_checker,
    }

    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which == "all":
        for fn in demos.values():
            try:
                fn()
            except Exception as e:
                print(f"Error in {fn.__name__}: {e}")
    elif which in demos:
        demos[which]()
    else:
        print(f"Usage: python standalone_usage.py [1|2|3|4|5|6|all]")
