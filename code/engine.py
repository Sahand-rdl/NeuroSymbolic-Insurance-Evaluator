import json
import logging
import httpx
from typing import Any, Dict, List
from pydantic import ValidationError

from code.config import ACTIVE_PROVIDER, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_MODEL, ANTHROPIC_MODEL, GEMINI_MODEL
from code.schema import VLMDecision
from code.dataloader import ClaimContext
from code.post_auditor import audit_vlm_decision
from code.prompts import build_system_prompt
from code.cache import DiskCache
from code.image_utils import process_and_encode_image
from code.request_manager import AsyncRequestManager

logger = logging.getLogger(__name__)

class VerificationEngine:
    def __init__(self, provider: str = ACTIVE_PROVIDER, use_cache: bool = True, max_concurrent: int = 10):
        self.provider = provider.lower()
        self.system_prompt = build_system_prompt()
        self.cache = DiskCache() if use_cache else None
        self.request_manager = AsyncRequestManager(max_concurrent=max_concurrent)
        
        # Mapping to cheap models for text tasks
        self.cheap_models = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-haiku-4-5-20251001",
            "gemini": "gemini-1.5-flash"
        }

    async def _call_openai(self, prompt_text: str, base64_images: List[Dict[str, str]] = None, model: str = OPENAI_MODEL, system_prompt_override: str = None, max_tokens: int = 1000) -> tuple[str, list]:
        sys_prompt = system_prompt_override if system_prompt_override is not None else self.system_prompt
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        content = [{"type": "text", "text": prompt_text}]
        if base64_images:
            for img in base64_images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img['b64']}"
                    }
                })
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": content}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"], []

    async def _call_anthropic(self, prompt_text: str, base64_images: List[Dict[str, str]] = None, model: str = ANTHROPIC_MODEL, system_prompt_override: str = None, max_tokens: int = 1000) -> tuple[str, List[Dict]]:
        sys_prompt = system_prompt_override if system_prompt_override is not None else self.system_prompt
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        # We define the retrieval tool schema
        tools = [{
            "name": "retrieval_tool",
            "description": "Search, read, or grep files to find exact evidence requirements.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["search", "read", "grep"]},
                    "target": {"type": "string"}
                },
                "required": ["mode", "target"]
            }
        }]

        content = []
        if base64_images:
            for img in base64_images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img['b64']
                    }
                })
        content.append({"type": "text", "text": prompt_text})
        
        messages = [{"role": "user", "content": content}]
        
        tool_calls_made = []
        
        import os
        async def execute_tool(mode, target):
            try:
                if mode == "read":
                    if not os.path.exists(target): return f"File not found: {target}"
                    with open(target, 'r') as f: return f.read()
                elif mode == "search":
                    import glob
                    files = glob.glob(f"**/*{target}*", recursive=True)
                    return "\\n".join(files) if files else "No matches found."
                elif mode == "grep":
                    import subprocess
                    result = subprocess.run(["grep", "-rn", target, "dataset/"], capture_output=True, text=True)
                    return result.stdout if result.stdout else "No matches found."
                return "Invalid mode."
            except Exception as e:
                return str(e)

        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                payload = {
                    "model": model,
                    "system": [{"type": "text", "text": sys_prompt, "cache_control": {"type": "ephemeral"}}],
                    "messages": messages,
                    "tools": tools,
                    "max_tokens": max_tokens,
                    "temperature": 0.0
                }
                
                response = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                response_message = {"role": "assistant", "content": data["content"]}
                messages.append(response_message)
                
                if data["stop_reason"] == "tool_use":
                    tool_content = []
                    for block in data["content"]:
                        if block["type"] == "tool_use":
                            tool_calls_made.append(block)
                            args = block["input"]
                            result_text = await execute_tool(args.get("mode"), args.get("target"))
                            tool_content.append({
                                "type": "tool_result",
                                "tool_use_id": block["id"],
                                "content": result_text
                            })
                    messages.append({"role": "user", "content": tool_content})
                else:
                    final_text = next((b["text"] for b in data["content"] if b["type"] == "text"), "")
                    return final_text, tool_calls_made

    async def _call_gemini(self, prompt_text: str, base64_images: List[Dict[str, str]] = None, model: str = GEMINI_MODEL, system_prompt_override: str = None, max_tokens: int = 1000) -> tuple[str, list]:
        sys_prompt = system_prompt_override if system_prompt_override is not None else self.system_prompt
        headers = {"Content-Type": "application/json"}
        parts = []
        parts.append({"text": sys_prompt + "\n\n" + prompt_text})
        if base64_images:
            for img in base64_images:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img['b64']
                    }
                })
        
        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens}
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"], []

    async def generate_text_only(self, prompt_text: str, model_tier: str = "cheap") -> str:
        """Helper to invoke cheap models for text summarization without images."""
        target_model = self.cheap_models[self.provider] if model_tier == "cheap" else None
        
        # Crucial fix: Override the system prompt so it does NOT output JSON or hallucinate review verdicts.
        sys_prompt_override = "You are a highly concise factual summarization assistant. Output ONLY the plain text summary. Absolutely NO JSON, formatting, or conversational filler."
        
        if self.provider == "openai":
            res, _ = await self.request_manager.execute(self._call_openai, prompt_text, None, target_model or OPENAI_MODEL, sys_prompt_override, 150)
            return res
        elif self.provider == "anthropic":
            res, _ = await self.request_manager.execute(self._call_anthropic, prompt_text, None, target_model or ANTHROPIC_MODEL, sys_prompt_override, 150)
            return res
        elif self.provider == "gemini":
            res, _ = await self.request_manager.execute(self._call_gemini, prompt_text, None, target_model or GEMINI_MODEL, sys_prompt_override, 150)
            return res
        raise ValueError(f"Unknown provider: {self.provider}")

    async def process_claim(self, context: ClaimContext) -> VLMDecision:
        # Prepare Images safely
        base64_images = []
        for path in context.image_paths:
            try:
                # Use our new optimized image scaler
                b64 = process_and_encode_image(path, max_edge=1024, quality=85)
                base64_images.append({"b64": b64, "path": path})
            except Exception as e:
                logger.error(f"Failed to process image {path}: {e}")
                
        # Load evidence requirements
        import csv
        evidence_rules = []
        try:
            with open('dataset/evidence_requirements.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['claim_object'] == 'all' or row['claim_object'] == context.claim_object:
                        evidence_rules.append(f"- {row['requirement_id']}: {row['minimum_image_evidence']}")
        except Exception as e:
            logger.error(f"Failed to read evidence_requirements.csv: {e}")
            evidence_rules.append("Failed to load rules.")
            
        rules_text = "\n".join(evidence_rules)
                
        # Build prompt text
        image_names = [path.split('/')[-1] for path in context.image_paths]
        prompt_text = (
            f"User ID: {context.user_id}\n"
            f"Claim Object: {context.claim_object}\n"
            f"User Claim: {context.user_claim}\n"
            f"History Summary: {context.history_summary}\n"
            f"History Flags: {context.history_flags}\n"
            f"Provided Images: {', '.join(image_names)}\n\n"
            f"MINIMUM EVIDENCE STANDARDS TO CHECK:\n{rules_text}\n"
        )
        cache_key = {
            "provider": self.provider,
            "prompt_text": prompt_text,
            "images": [img["path"] for img in base64_images],
            "type": "unified_v2"
        }
        
        try:
            # Single unified API call
            raw_response = None
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached and "raw_response" in cached:
                    raw_response = cached["raw_response"]
            
            if raw_response is None:
                if self.provider == "openai":
                    raw_response, _ = await self.request_manager.execute(self._call_openai, prompt_text, base64_images)
                elif self.provider == "anthropic":
                    raw_response, _ = await self.request_manager.execute(self._call_anthropic, prompt_text, base64_images)
                elif self.provider == "gemini":
                    raw_response, _ = await self.request_manager.execute(self._call_gemini, prompt_text, base64_images)
                else:
                    raise ValueError(f"Unknown provider")
                    
                if self.cache: self.cache.set(cache_key, {"raw_response": raw_response})
            
            import re
            def extract_json(text):
                match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
                if match: return json.loads(match.group(0))
                raise ValueError("No JSON found")
                
            parsed = extract_json(raw_response)
            
            # Normalize risk_flags from the unified response
            raw_flags = parsed.get("risk_flags", [])
            if isinstance(raw_flags, list):
                risk_flags = [f for f in raw_flags if isinstance(f, str) and f != "none"]
            else:
                risk_flags = []
            
            # Deterministic: Clean up contradictory risk flags based on decisions
            claim_status = parsed.get("claim_status", "unknown")
            issue_type = parsed.get("issue_type", "unknown")
            
            # If supported, there is no claim mismatch or damage_not_visible
            if claim_status == "supported":
                if "claim_mismatch" in risk_flags: risk_flags.remove("claim_mismatch")
                if "damage_not_visible" in risk_flags: risk_flags.remove("damage_not_visible")
            
            # If contradicted and no damage found, damage is definitely not visible
            if claim_status == "contradicted" and issue_type == "none":
                if "damage_not_visible" not in risk_flags:
                    risk_flags.append("damage_not_visible")
                    
            # If not enough info because it's cropped or wrong angle, add damage_not_visible
            if claim_status == "not_enough_information" and ("cropped_or_obstructed" in risk_flags or "wrong_angle" in risk_flags):
                if "damage_not_visible" not in risk_flags:
                    risk_flags.append("damage_not_visible")

            # Deterministic: Add user_history_risk from CSV data (not VLM guessing)
            if context.history_flags:
                history_flags = [f.strip() for f in context.history_flags.split(";")]
                for hf in history_flags:
                    if hf and hf != "none" and hf not in risk_flags:
                        risk_flags.append(hf)
            
            # Deterministic: Add manual_review_required based on fraud-indicative trigger flags
            # Note: damage_not_visible and cropped_or_obstructed alone do NOT trigger manual review
            triggers = ["wrong_object", "claim_mismatch", "non_original_image", "text_instruction_present", "user_history_risk"]
            if any(t in risk_flags for t in triggers):
                if "manual_review_required" not in risk_flags:
                    risk_flags.append("manual_review_required")
            
            risk_flags = sorted(list(set(risk_flags)))
            if len(risk_flags) == 0:
                risk_flags = ["none"]
                
            parsed["risk_flags"] = risk_flags
            parsed["cited_paths"] = []
            decision = VLMDecision(**parsed)
            return audit_vlm_decision(decision)
            
        except Exception as e:
            logger.error(f"Execution or Validation failed: {e}")
            return self._fallback_decision()

    def _fallback_decision(self) -> VLMDecision:
        decision = VLMDecision(
            evidence_standard_met=False,
            evidence_standard_met_reason="Failed to process image or API failure.",
            risk_flags=["none"],
            issue_type="unknown",
            object_part="unknown",
            claim_status="not_enough_information",
            claim_status_justification="Automated fallback due to processing error.",
            supporting_image_ids=["none"],
            valid_image=False,
            severity="unknown"
        )
        return audit_vlm_decision(decision)
