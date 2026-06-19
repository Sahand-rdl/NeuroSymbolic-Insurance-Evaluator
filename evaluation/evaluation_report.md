# Operational Analysis Report

## Model Calls & Images Processed
- **Model Calls (Sample Set)**: 20 calls (1 call per claim, as the pre-LLM summarizer was disabled to reduce latency and preserve contextual fidelity).
- **Model Calls (Test Set)**: 44 calls (1 call per claim).
- **Number of Images Processed**: ~30 for the sample set and ~66 for the test set (averaging 1.5 images per claim).

## Token Usage & Cost (Approximate)
- **Average Input Tokens per claim**: ~3,000 tokens (system prompt + user claim + 1-2 dynamically resized images).
- **Average Output Tokens per claim**: ~150 tokens (structured JSON response).
- **Total Input Tokens (Test Set)**: ~132,000 tokens.
- **Total Output Tokens (Test Set)**: ~6,600 tokens.
- **Approximate Cost for Full Test Set**: Assuming Claude 3.5 Sonnet pricing ($3.00/1M input, $15.00/1M output), the input cost is ~$0.40 and the output cost is ~$0.10, yielding a **total approximate cost of ~$0.50** for the entire test set.

## Latency & Runtime
- **Single Claim Latency**: 3-6 seconds per request.
- **Full Test Set Runtime**: With the `VerificationEngine` executing an `asyncio.gather` batch processing pipeline with a concurrency limit (`max_concurrent=10`), processing the full 44 claims takes roughly **30-40 seconds** total, effectively nullifying the cumulative sequential latency bottleneck.

## Rate Limits & Infrastructure Strategies
- **Concurrency & Throttling**: We utilize an `asyncio.Semaphore(max_concurrent)` within our `RequestManager` to limit parallel API calls. This strict concurrency bounds the requests per minute (RPM) to avoid triggering HTTP 429 (Too Many Requests) errors from the LLM provider.
- **Caching**: The system implements an SQLite-backed caching mechanism in `cache.py`. All API requests are hashed and persisted locally, meaning subsequent identical runs during development or identical claims in production skip the network entirely, resulting in zero cost and zero latency.
- **Retry Strategy with Exponential Backoff**: Any intermittent network errors, LLM provider downtime, or strict rate limit rejections are intercepted by the `RequestManager`, which automatically retries with exponential backoff rather than failing the claim processing outright.
- **Image Downsampling**: Before transmission, images are dynamically compressed via `image_utils.py` to bound token expenditure while remaining structurally clear enough for evidence evaluation.
