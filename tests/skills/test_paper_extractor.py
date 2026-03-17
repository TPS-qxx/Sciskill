"""
Tests for PaperStructuralExtractor.

All tests mock external calls (LLM, ArXiv, S2) so they run offline and fast.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sciskills.skills.paper_extractor import PaperStructuralExtractor
from sciskills.skills.paper_extractor.skill import _cap_confidence, _fields_for_mode, _max_tokens_for_mode


# ── Helpers ─────────────────────────────────────────────────────────────── #

ARXIV_META = {
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani"],
    "year": 2017,
    "venue": "NeurIPS",
    "abstract": "We propose a new simple network architecture, the Transformer.",
}

FULL_LLM_RESPONSE = {
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani"],
    "year": "2017",
    "venue": "NeurIPS",
    "abstract": "We propose a new simple network architecture, the Transformer.",
    "research_question": {
        "value": "Can attention mechanisms replace recurrent networks entirely?",
        "evidence": ["We propose a new simple network architecture, the Transformer."],
        "confidence": 0.92,
    },
    "problem_statement": {
        "value": "RNNs are slow and hard to parallelize.",
        "evidence": ["Sequential computation forms the fundamental constraint."],
        "confidence": 0.88,
    },
    "methodology": {
        "approach": "Self-attention based encoder-decoder",
        "model_architecture": "Transformer",
        "key_techniques": ["multi-head attention", "positional encoding"],
        "novelty": "Replaces recurrence with attention entirely",
        "confidence": 0.95,
    },
    "datasets": [{"name": "WMT 2014 EN-DE", "version": None, "scale": "4.5M sentence pairs",
                  "domain": "translation", "public": True, "url": None}],
    "baselines": [{"name": "ByteNet", "paper_ref": None, "type": "prior_work"}],
    "metrics": [{"name": "BLEU", "value": "28.4", "dataset": "WMT EN-DE", "is_best": True,
                 "evidence": "achieving 28.4 BLEU, improving over existing best results"}],
    "main_findings": [{"claim": "Transformer achieves SOTA on MT.", "evidence": ["28.4 BLEU"], "confidence": 0.93}],
    "implementation_details": {"code_available": True, "code_url": None, "hardware": "8 P100 GPUs", "training_time": "12h"},
    "limitations": ["Only evaluated on translation tasks."],
    "future_work": ["Apply to other tasks beyond MT."],
}


def _make_skill() -> PaperStructuralExtractor:
    return PaperStructuralExtractor()


def _mock_arxiv(meta: dict = ARXIV_META):
    m = MagicMock()
    m.get_paper.return_value = meta
    return m


def _mock_s2(meta: dict = ARXIV_META):
    m = MagicMock()
    m.get_by_arxiv.return_value = {"venue": meta.get("venue", ""), "year": meta.get("year")}
    m.get_by_doi.return_value = {
        "title": meta.get("title", ""),
        "authors": [{"name": n} for n in meta.get("authors", [])],
        "year": meta.get("year"),
        "venue": meta.get("venue", ""),
        "abstract": meta.get("abstract", ""),
        "tldr": None,
    }
    return m


def _mock_llm(response: dict):
    m = MagicMock()
    m.chat_json.return_value = response
    return m


# ── Unit: mode helpers ───────────────────────────────────────────────────── #

def test_fields_for_mode_metadata():
    f = _fields_for_mode("metadata")
    assert "title" in f
    assert "research_question" not in f
    assert "limitations" not in f


def test_fields_for_mode_method():
    f = _fields_for_mode("method")
    assert "research_question" in f
    assert "metrics" not in f


def test_fields_for_mode_full():
    f = _fields_for_mode("full")
    assert "limitations" in f
    assert "future_work" in f


def test_max_tokens_increases_with_mode():
    assert _max_tokens_for_mode("metadata") < _max_tokens_for_mode("method")
    assert _max_tokens_for_mode("method") < _max_tokens_for_mode("experiment")
    assert _max_tokens_for_mode("experiment") < _max_tokens_for_mode("full")


# ── Unit: confidence capping ──────────────────────────────────────────────── #

def test_cap_confidence_single():
    obj = {"confidence": 0.95}
    assert _cap_confidence(obj, 0.65)["confidence"] == 0.65


def test_cap_confidence_nested():
    obj = {
        "research_question": {"value": "x", "confidence": 0.90},
        "main_findings": [{"confidence": 0.85}],
    }
    capped = _cap_confidence(obj, 0.65)
    assert capped["research_question"]["confidence"] == 0.65
    assert capped["main_findings"][0]["confidence"] == 0.65


def test_cap_confidence_preserves_low():
    obj = {"confidence": 0.40}
    assert _cap_confidence(obj, 0.65)["confidence"] == 0.40


def test_cap_confidence_ignores_non_confidence_keys():
    obj = {"value": "hello", "score": 0.99}
    result = _cap_confidence(obj, 0.65)
    assert result["score"] == 0.99  # key is 'score', not 'confidence' — untouched


# ── Integration: metadata mode (no LLM) ─────────────────────────────────── #

def test_metadata_mode_no_llm_call():
    skill = _make_skill()
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client") as mock_llm_factory:

        result = skill({"arxiv_id": "1706.03762", "mode": "metadata"})

    assert result.success
    # LLM should NOT have been called for metadata mode with API source
    mock_llm_factory.assert_not_called()
    assert result.data["title"] == "Attention Is All You Need"
    assert result.data["_extraction_meta"]["mode"] == "metadata"


def test_metadata_mode_output_has_no_method_fields():
    skill = _make_skill()
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()):

        result = skill({"arxiv_id": "1706.03762", "mode": "metadata"})

    assert result.success
    assert "research_question" not in result.data
    assert "methodology" not in result.data
    assert "limitations" not in result.data


# ── Integration: full mode with LLM ─────────────────────────────────────── #

def test_full_mode_calls_llm():
    skill = _make_skill()
    mock_llm = _mock_llm(FULL_LLM_RESPONSE)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "full"})

    assert result.success
    mock_llm.chat_json.assert_called_once()


def test_full_mode_output_has_evidence_fields():
    skill = _make_skill()
    mock_llm = _mock_llm(FULL_LLM_RESPONSE)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "full"})

    rq = result.data["research_question"]
    assert "value" in rq
    assert "evidence" in rq
    assert isinstance(rq["evidence"], list)
    assert "confidence" in rq
    assert isinstance(rq["confidence"], float)


def test_full_mode_has_limitations_and_future_work():
    skill = _make_skill()
    mock_llm = _mock_llm(FULL_LLM_RESPONSE)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "full"})

    assert "limitations" in result.data
    assert "future_work" in result.data


def test_extraction_meta_present():
    skill = _make_skill()
    mock_llm = _mock_llm(FULL_LLM_RESPONSE)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "full"})

    meta = result.data["_extraction_meta"]
    assert meta["mode"] == "full"
    assert meta["source"] == "arxiv:1706.03762"
    assert isinstance(meta["full_text_used"], bool)
    assert isinstance(meta["warnings"], list)


# ── Confidence capping on abstract-only sources ───────────────────────────── #

def test_confidence_capped_for_arxiv_source():
    skill = _make_skill()
    high_confidence_response = dict(FULL_LLM_RESPONSE)
    high_confidence_response["research_question"] = {
        "value": "test", "evidence": ["test"], "confidence": 0.95
    }
    mock_llm = _mock_llm(high_confidence_response)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "full"})

    # arXiv → abstract_only warning → confidence capped at 0.65
    assert result.data["research_question"]["confidence"] <= 0.65


# ── Mode: method ─────────────────────────────────────────────────────────── #

def test_method_mode_requests_smaller_token_budget():
    skill = _make_skill()
    method_response = {k: v for k, v in FULL_LLM_RESPONSE.items()
                       if k not in ("metrics", "main_findings", "implementation_details",
                                    "limitations", "future_work")}
    mock_llm = _mock_llm(method_response)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "1706.03762", "mode": "method"})

    assert result.success
    call_kwargs = mock_llm.chat_json.call_args[1]
    assert call_kwargs["max_tokens"] == _max_tokens_for_mode("method")


# ── Invalid mode ─────────────────────────────────────────────────────────── #

def test_invalid_mode_raises_validation_error():
    import jsonschema
    skill = _make_skill()
    with pytest.raises(jsonschema.ValidationError):
        skill({"arxiv_id": "1706.03762", "mode": "banana"})


# ── DOI source ───────────────────────────────────────────────────────────── #

def test_doi_source_metadata_mode():
    skill = _make_skill()
    with patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client") as mock_llm_factory:

        result = skill({"doi": "10.1145/3292500.3330919", "mode": "metadata"})

    # metadata mode + API source → no LLM
    mock_llm_factory.assert_not_called()
    assert result.success
    assert result.data["_extraction_meta"]["mode"] == "metadata"


# ── arxiv_id field in output ─────────────────────────────────────────────── #

def test_arxiv_id_in_output():
    skill = _make_skill()
    mock_llm = _mock_llm(FULL_LLM_RESPONSE)
    with patch("sciskills.skills.paper_extractor.skill.ArxivClient", return_value=_mock_arxiv()), \
         patch("sciskills.skills.paper_extractor.skill.SemanticScholarClient", return_value=_mock_s2()), \
         patch("sciskills.skills.paper_extractor.skill.get_default_client", return_value=mock_llm):

        result = skill({"arxiv_id": "arxiv:1706.03762", "mode": "full"})

    assert result.data["arxiv_id"] == "1706.03762"   # 'arxiv:' prefix stripped
    assert result.data["doi"] is None
