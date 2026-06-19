from typing import List, Literal
from pydantic import BaseModel, Field, field_serializer

# Define strict Literals as specified in problem_statement.md
IssueType = Literal[
    "dent",
    "scratch",
    "crack",
    "glass_shatter",
    "broken_part",
    "missing_part",
    "torn_packaging",
    "crushed_packaging",
    "water_damage",
    "stain",
    "none",
    "unknown"
]

ObjectPart = Literal[
    # Car parts
    "front_bumper",
    "rear_bumper",
    "door",
    "hood",
    "windshield",
    "side_mirror",
    "headlight",
    "taillight",
    "fender",
    "quarter_panel",
    "body",
    # Laptop parts
    "screen",
    "keyboard",
    "trackpad",
    "hinge",
    "lid",
    "corner",
    "port",
    "base",
    # Package parts
    "box",
    "package_corner",
    "package_side",
    "seal",
    "label",
    "contents",
    "item",
    # General
    "unknown"
]

RiskFlag = Literal[
    "none",
    "blurry_image",
    "cropped_or_obstructed",
    "low_light_or_glare",
    "wrong_angle",
    "wrong_object",
    "wrong_object_part",
    "damage_not_visible",
    "claim_mismatch",
    "possible_manipulation",
    "non_original_image",
    "text_instruction_present",
    "user_history_risk",
    "manual_review_required"
]

ClaimStatus = Literal["supported", "contradicted", "not_enough_information", "escalated"]

Severity = Literal[
    "none",
    "low",
    "medium",
    "high",
    "unknown"
]

class RiskFlagsEval(BaseModel):
    blurry_image: bool
    cropped_or_obstructed: bool
    low_light_or_glare: bool
    wrong_angle: bool
    wrong_object: bool
    wrong_object_part: bool
    damage_not_visible: bool
    claim_mismatch: bool
    possible_manipulation: bool
    non_original_image: bool
    text_instruction_present: bool

class VLMDecision(BaseModel):
    """
    Structured model for the raw decision returned by the VLM.
    """
    evidence_standard_met: bool
    evidence_standard_met_reason: str
    risk_flags: List[RiskFlag]
    issue_type: IssueType
    object_part: ObjectPart
    claim_status: ClaimStatus
    claim_status_justification: str
    supporting_image_ids: List[str]  # Use ["none"] if none
    valid_image: bool
    severity: Severity
    cited_paths: List[str] = Field(default_factory=list)

class OutputRow(VLMDecision):
    """
    Model representing a row in output.csv, matching the expected columns in order.
    """
    user_id: str
    image_paths: str
    user_claim: str
    claim_object: str
    evidence_standard_met: bool
    evidence_standard_met_reason: str
    risk_flags: List[RiskFlag]
    issue_type: IssueType
    object_part: ObjectPart
    claim_status: ClaimStatus
    claim_status_justification: str
    supporting_image_ids: List[str]
    valid_image: bool
    severity: Severity

    @field_serializer("evidence_standard_met", "valid_image", when_used="always")
    def serialize_bool(self, v: bool) -> str:
        return "true" if v else "false"

    @field_serializer("risk_flags", when_used="always")
    def serialize_risk_flags(self, v: List[RiskFlag]) -> str:
        if not v:
            return "none"
        if len(v) == 1 and v[0] == "none":
            return "none"
        filtered = [f for f in v if f != "none"]
        if not filtered:
            return "none"
        return ";".join(filtered)

    @field_serializer("supporting_image_ids", when_used="always")
    def serialize_supporting_image_ids(self, v: List[str]) -> str:
        if not v:
            return "none"
        if len(v) == 1 and v[0] == "none":
            return "none"
        filtered = [img for img in v if img != "none"]
        if not filtered:
            return "none"
        return ";".join(filtered)

    @classmethod
    def from_decision(
        cls,
        user_id: str,
        image_paths: str,
        user_claim: str,
        claim_object: str,
        decision: VLMDecision
    ) -> "OutputRow":
        return cls(
            user_id=user_id,
            image_paths=image_paths,
            user_claim=user_claim,
            claim_object=claim_object,
            evidence_standard_met=decision.evidence_standard_met,
            evidence_standard_met_reason=decision.evidence_standard_met_reason,
            risk_flags=decision.risk_flags,
            issue_type=decision.issue_type,
            object_part=decision.object_part,
            claim_status=decision.claim_status,
            claim_status_justification=decision.claim_status_justification,
            supporting_image_ids=decision.supporting_image_ids,
            valid_image=decision.valid_image,
            severity=decision.severity,
        )
