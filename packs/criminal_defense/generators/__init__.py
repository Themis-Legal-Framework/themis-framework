"""Document generators for criminal defense practice pack."""

from __future__ import annotations

from packs.criminal_defense.generators.base import BaseGenerator, Section
from packs.criminal_defense.generators.brady import BradyChecklistGenerator
from packs.criminal_defense.generators.constitutional import ConstitutionalAnalysisGenerator
from packs.criminal_defense.generators.discovery import DiscoveryDemandGenerator
from packs.criminal_defense.generators.interview import WitnessInterviewGenerator
from packs.criminal_defense.generators.preservation import PreservationLetterGenerator
from packs.criminal_defense.generators.recommendations import MotionRecommendationsGenerator
from packs.criminal_defense.generators.suppression import SuppressionMotionGenerator
from packs.criminal_defense.generators.timeline import TimelineGenerator

__all__ = [
    "BaseGenerator",
    "BradyChecklistGenerator",
    "ConstitutionalAnalysisGenerator",
    "DiscoveryDemandGenerator",
    "MotionRecommendationsGenerator",
    "PreservationLetterGenerator",
    "Section",
    "SuppressionMotionGenerator",
    "TimelineGenerator",
    "WitnessInterviewGenerator",
]
