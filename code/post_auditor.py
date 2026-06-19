from code.schema import VLMDecision

def audit_vlm_decision(decision: VLMDecision) -> VLMDecision:
    """
    Applies strict deterministic rules to override the VLM decision for self-consistency.
    """
    # Rule: If image is invalid, override to not_enough_information.
    if not decision.valid_image:
        decision.claim_status = "not_enough_information"

    # NOTE: We intentionally do NOT override claim_status based on risk_flags.
    # The VLM has the visual context and is the final authority on claim_status.
    # Overriding based on risk_flags causes cascading errors when flags are wrong.
        
    return decision

