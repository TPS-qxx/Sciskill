"""Tests for BibTeXFixerEnricher — no network calls required."""
import pytest
from unittest.mock import patch, MagicMock

from sciskills.skills.bibtex_fixer import BibTeXFixerEnricher
from sciskills.skills.bibtex_fixer.rules import (
    check_missing_fields,
    check_author_format,
    check_year_format,
    find_duplicate_entries,
    normalize_author,
    run_all_checks,
)


SAMPLE_BIB = """\
@article{vaswani2017attention,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki},
  journal = {Advances in Neural Information Processing Systems},
  year = {2017},
  doi = {10.48550/arXiv.1706.03762}
}

@inproceedings{devlin2019bert,
  title = {{BERT}: Pre-training of Deep Bidirectional Transformers},
  author = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton},
  booktitle = {Proceedings of NAACL},
  year = {2019}
}
"""

MISSING_FIELD_BIB = """\
@article{missingjournal,
  title = {Some Paper},
  author = {Smith, John},
  year = {2020}
}
"""

DUPLICATE_BIB = """\
@article{paper1,
  title = {Same Title},
  author = {A, B},
  journal = {J1},
  year = {2021},
  doi = {10.1234/same}
}
@article{paper2,
  title = {Same Title},
  author = {A, B},
  journal = {J2},
  year = {2021},
  doi = {10.1234/same}
}
"""


# ------------------------------------------------------------------ #
# Rule unit tests                                                      #
# ------------------------------------------------------------------ #

def test_check_missing_fields_article():
    entry = {"ENTRYTYPE": "article", "ID": "x", "title": "T", "author": "A", "year": "2020"}
    issues = check_missing_fields(entry)
    assert any("journal" in i.issue for i in issues)


def test_check_missing_fields_ok():
    entry = {
        "ENTRYTYPE": "article", "ID": "x",
        "title": "T", "author": "A", "journal": "J", "year": "2020"
    }
    issues = check_missing_fields(entry)
    assert len(issues) == 0


def test_check_author_mixed_format():
    entry = {"ENTRYTYPE": "article", "ID": "x", "author": "Smith, John and Alice Brown"}
    issues = check_author_format(entry)
    assert any("Inconsistent" in i.issue for i in issues)


def test_check_author_consistent():
    entry = {"ENTRYTYPE": "article", "ID": "x", "author": "Smith, John and Brown, Alice"}
    issues = check_author_format(entry)
    assert len(issues) == 0


def test_check_year_invalid():
    entry = {"ENTRYTYPE": "article", "ID": "x", "year": "20xx"}
    issues = check_year_format(entry)
    assert len(issues) > 0


def test_check_year_valid():
    entry = {"ENTRYTYPE": "article", "ID": "x", "year": "2023"}
    issues = check_year_format(entry)
    assert len(issues) == 0


def test_find_duplicates_by_doi():
    entries = [
        {"ID": "a", "doi": "10.1234/same", "title": "X"},
        {"ID": "b", "doi": "10.1234/same", "title": "Y"},
    ]
    issues = find_duplicate_entries(entries)
    assert any(i.action == "removed" for i in issues)


def test_normalize_author_first_last():
    result = normalize_author("John Smith and Alice Brown")
    assert "Smith, John" in result
    assert "Brown, Alice" in result


def test_normalize_author_already_normalized():
    result = normalize_author("Smith, John and Brown, Alice")
    assert result == "Smith, John and Brown, Alice"


# ------------------------------------------------------------------ #
# Skill integration tests (with mocked bibtexparser)                   #
# ------------------------------------------------------------------ #

def test_skill_parses_valid_bibtex():
    skill = BibTeXFixerEnricher()
    with patch.object(skill, "_enrich_entry", return_value=False):
        try:
            result = skill({
                "bibtex_str": SAMPLE_BIB,
                "auto_enrich": False,
                "remove_duplicates": True,
                "normalize_authors": True,
            })
        except ImportError:
            pytest.skip("bibtexparser not installed")
    assert result.success
    assert result.data["stats"]["total"] == 2


def test_skill_detects_missing_fields():
    skill = BibTeXFixerEnricher()
    with patch.object(skill, "_enrich_entry", return_value=False):
        try:
            result = skill({
                "bibtex_str": MISSING_FIELD_BIB,
                "auto_enrich": False,
            })
        except ImportError:
            pytest.skip("bibtexparser not installed")
    assert result.success
    issue_texts = [i["issue"] for i in result.data["issues_found"]]
    assert any("journal" in t for t in issue_texts)


def test_skill_removes_duplicates():
    skill = BibTeXFixerEnricher()
    with patch.object(skill, "_enrich_entry", return_value=False):
        try:
            result = skill({
                "bibtex_str": DUPLICATE_BIB,
                "auto_enrich": False,
                "remove_duplicates": True,
            })
        except ImportError:
            pytest.skip("bibtexparser not installed")
    assert result.success
    assert result.data["stats"]["duplicates_removed"] >= 1
    assert result.data["stats"]["remaining"] < result.data["stats"]["total"]
