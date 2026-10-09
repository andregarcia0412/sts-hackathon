"""How the state judge runs. Recorded in every analysis (`AnalysisVersions.judge`) and benchmark config."""

from typing import Literal

from pydantic import BaseModel

from backend.config import Settings

# `force` exists only in the re-judge benchmark: a diagnostic ceiling, never used in a real analysis.
CoherenceMode = Literal["off", "flag", "reask", "force"]
JudgeMode = Literal["estado", "questionario"]


class JudgeOptions(BaseModel):
    judge_mode: JudgeMode = "estado"  # estado = the LLM picks the label; questionario = answers → table in code
    coherence_mode: CoherenceMode = "off"
    coherence_high: int = 75
    coherence_low: int = 25
    coherence_min_rules: int = 4

    @classmethod
    def from_settings(cls, settings: Settings, **overrides) -> "JudgeOptions":
        values = {
            "judge_mode": settings.judge_mode,
            "coherence_mode": settings.coherence_mode,
            "coherence_high": settings.coherence_high,
            "coherence_low": settings.coherence_low,
            "coherence_min_rules": settings.coherence_min_rules,
        }
        return cls(**values | {k: v for k, v in overrides.items() if v is not None})
