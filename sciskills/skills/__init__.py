# Import all skills to trigger registry.register decorators
from sciskills.skills.paper_extractor import PaperStructuralExtractor
from sciskills.skills.bibtex_fixer import BibTeXFixerEnricher
from sciskills.skills.experiment_comparator import ExperimentResultComparator
from sciskills.skills.statistical_advisor import StatisticalTestAdvisor
from sciskills.skills.gap_identifier import ResearchGapIdentifier
from sciskills.skills.reproducibility_checker import ReproducibilityChecker

__all__ = [
    "PaperStructuralExtractor",
    "BibTeXFixerEnricher",
    "ExperimentResultComparator",
    "StatisticalTestAdvisor",
    "ResearchGapIdentifier",
    "ReproducibilityChecker",
]
