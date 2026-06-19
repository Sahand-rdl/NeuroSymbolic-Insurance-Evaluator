# HackerRank Orchestrate - June 2026
## Multi-Modal Evidence Review System

This repository contains an end-to-end multi-modal evidence review pipeline designed to verify damage claims. The system relies on Vision-Language Models (Claude 4.6 Sonnet / Gemini) augmented with deterministic rule engines to process text claims alongside multiple image attachments.

---

## 1. System Architecture

The pipeline consists of the following core modules:
- **`main.py`**: The orchestration script. Handles concurrency, input/output management, and overall execution flow.
- **`engine.py`**: The core verification logic. It fetches data, coordinates the API request to the VLM, and runs deterministic post-processing on the JSON output.
- **`prompts.py`**: The centralized intelligence hub containing the strict system prompt, enum definitions, and anti-hallucination rules.
- **`schema.py`**: Pydantic models defining the exact expected JSON output from the VLM.
- **`post_auditor.py`**: A deterministic layer that enforces hard logical constraints (e.g., if an image is unreadable, it forces `claim_status` to `not_enough_information`).
- **`dataloader.py` & `image_utils.py`**: Helpers for parsing CSV relationships, base64 encoding images, and resizing large images.
- **`cache.py` & `request_manager.py`**: Disk-caching for reproducibility without spending API credits, and async retry logic with exponential backoff for API robustness.

---

## 2. Engineering Choices: What Failed vs. What Succeeded

Building this architecture wasn't a straight line. We spent over 12 hours on intense experimentation, scaffolding, trial and error, and prompt engineering. Here is the chronological evolution of the pipeline:

### 1. The Haiku Summarizer (Failed)
**Attempt:** We initially attempted extreme token optimization and injection handling by using a cheap, smaller model to summarize the conversational claims into a single sentence before passing them to the primary VLM. 
**Result:** It backfired completely. The primary VLM lost crucial nuance and specific user phrasing, severely degrading accuracy.

### 2. The Boolean Risk Array (Failed)
**Attempt:** We defined our `risk_flags` output as a strict array of explicit booleans (`true`/`false`) for all 14 possible flags.
**Result:** This confused the model's spatial reasoning and pulled down the performance of *all other columns* in the output.

### 3. The "Separated" Two-Call Architecture (Failed)
**Attempt:** To fix the boolean issue without hurting the primary classification, we isolated the risk flags into a completely separate VLM prompt.
**Result ("Critic Bias"):** By telling the VLM its sole job was to hunt for fraud, it aggressively hallucinated risks to justify its own existence. It would flag perfectly valid, undamaged claims with `claim_mismatch` simply because it felt pressured to output a risk. This created a cascading failure where our post-auditor downgraded valid claims to `not_enough_information`.

### 4. The Unified Request + Deterministic Enforcer (Success!)
**Solution:** We merged the primary analysis and risk evaluation back into a **single, unified API request** for speed, cost, and accuracy. 
To prevent the model from outputting paradoxical JSON (e.g. `claim_status="supported"` but adding `claim_mismatch`), we built a **deterministic neuro-symbolic engine** (`engine.py`) to enforce boolean invariants, completely avoiding overfitting.

---

## 3. Resolving Internal Inconsistencies (The Hybrid Approach)

We handle cases where the user's text claims one thing, but the image shows something else by following an absolute rule: "The pixels determine the truth." If the user claims a cracked screen but shows a blurry image, we output `not_enough_information`. If they submit an image of a black car when the claim is for a white car, we explicitly flag `wrong_object` and fail the claim.

To ensure our JSON outputs don't contradict themselves, we use a Hybrid neuro-symbolic approach. The VLM provides the fuzzy visual reasoning, but a deterministic Python layer in `engine.py` enforces boolean invariants. For example, a `supported` claim is programmatically stripped of `claim_mismatch` flags, guaranteeing self-consistency without wasting API tokens on retry loops or risking overfitting in the prompt.

---

## 4. How to Run and Test

**Prerequisites:**
You need `ANTHROPIC_API_KEY` set in your environment.

**To Run the Evaluation (on sample data):**
```bash
# Clear cache if you want a fresh run
rm -rf .cache

# Run the pipeline
python code/main.py dataset/sample_claims.csv sample_output.csv

# Evaluate the accuracy
python code/evaluation/main.py dataset/sample_claims.csv sample_output.csv
```

**To Run the Final Submission:**
```bash
python code/main.py dataset/claims.csv output.csv
```
