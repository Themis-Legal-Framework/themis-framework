# LLM-COUNSEL Legal Prompts
from backend.prompts.personas import LEGAL_PERSONAS, LEAD_COUNSEL_PROMPT, get_persona
from backend.prompts.stage1 import build_stage1_prompt
from backend.prompts.stage2 import build_stage2_prompt
from backend.prompts.stage3 import build_stage3_prompt

__all__ = [
    "LEGAL_PERSONAS",
    "LEAD_COUNSEL_PROMPT",
    "get_persona",
    "build_stage1_prompt",
    "build_stage2_prompt",
    "build_stage3_prompt",
]
