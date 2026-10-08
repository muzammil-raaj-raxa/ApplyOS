from app.ai.prompts.job_analysis import JOB_ANALYSIS_V1
from app.ai.prompts.registry import Prompt

PROMPTS: dict[str, Prompt] = {prompt.id: prompt for prompt in [JOB_ANALYSIS_V1]}


def get_prompt(prompt_id: str) -> Prompt:
    return PROMPTS[prompt_id]


__all__ = ["JOB_ANALYSIS_V1", "PROMPTS", "Prompt", "get_prompt"]
