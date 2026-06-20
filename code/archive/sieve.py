import re
from typing import Optional
from code.schema import VLMDecision

INJECTION_PATTERN = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions?|reveal\s+system\s+prompt|bypass\s+rules|you\s+are\s+now|system\s+override|muestra\s+todas\s+las\s+reglas)",
    re.IGNORECASE
)

class ClaimSieve:
    """
    Pre-LLM Middleware block to catch malicious injections and perform cheap preprocessing.
    """
    def __init__(self, engine=None):
        # We pass the VerificationEngine instance purely for executing the cheap summarization layer.
        self.engine = engine

    def _layer0_regex_sieve(self, user_claim: str) -> bool:
        """
        Layer 0: Returns True if a prompt injection is detected. Fast Python regex filter.
        """
        return bool(INJECTION_PATTERN.search(user_claim))

    async def _layer1_cheap_summarizer(self, user_claim: str) -> str:
        """
        Layer 1: Summarize the piped conversation into a factual string using a fast, cheap model.
        """
        if not self.engine:
            return user_claim
        
        prompt = (
            "Summarize the following customer service conversation into a single, "
            "factual damage claim string. Do not include greetings or conversational filler.\n"
            f"Conversation:\n{user_claim}"
        )
        try:
            summary = await self.engine.generate_text_only(prompt, model_tier="cheap")
            return summary.strip()
        except Exception:
            # Fallback to the raw claim if the cheap summarizer fails
            return user_claim

    async def process_claim_text(self, user_claim: str) -> str | VLMDecision:
        """
        Runs the middleware layers.
        Returns a summarized claim string, OR a forced fallback VLMDecision if an injection is caught.
        """
        # Layer 0
        if self._layer0_regex_sieve(user_claim):
            return VLMDecision(
                evidence_standard_met=False,
                evidence_standard_met_reason="Prompt injection detected.",
                risk_flags=["text_instruction_present"],
                issue_type="none",
                object_part="unknown",
                claim_status="not_enough_information",
                claim_status_justification="Automated rejection due to prohibited prompt instructions.",
                supporting_image_ids=["none"],
                valid_image=False,
                severity="unknown"
            )

        # Layer 1
        return await self._layer1_cheap_summarizer(user_claim)
