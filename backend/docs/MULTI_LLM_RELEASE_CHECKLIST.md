# Multi-LLM Extraction (AbeAI-style) – Release Checklist

## Configuration & enablement

- **Enable:** Set `MULTI_LLM_EXTRACTION_ENABLED=true` in `.env` (or environment).
- **Provider keys:** At least one of the following must be set when multi-LLM is enabled:  
  `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `MISTRAL_API_KEY`, `GOOGLE_API_KEY`.
- **Tuning:** `MULTI_LLM_MAX_PROVIDERS` (default 3) caps parallel LLM calls; `MULTI_LLM_TIMEOUT_SEC` (default 120) applies per-call timeout.
- **Disable:** Set `MULTI_LLM_EXTRACTION_ENABLED=false` to use existing template/LLM flow only; no extra API calls.

## Security
- [ ] API keys (ANTHROPIC, OPENAI, PERPLEXITY, MISTRAL, GOOGLE) stored in `.env` or secrets manager only; never committed.
- [ ] Validate production env has required keys when `MULTI_LLM_EXTRACTION_ENABLED=true`.

## Hardening
- [ ] Timeouts: `MULTI_LLM_TIMEOUT_SEC` (default 120s) applied to external LLM calls.
- [ ] Rate limiting: consider per-run or per-tenant limits for LLM calls.
- [ ] Circuit breaker: optional – skip additional providers if total latency exceeds threshold.

## Observability
- [ ] Master JSON stored for every run (`extraction_runs` table).
- [ ] GET `/api/v1/extract/runs/{run_id}` and GET `/api/v1/extract/runs?document_upload_id=X` for metrics (latency, gate, telemetry by provider).
- [ ] Telemetry: per-model call count, token estimates, latency in `master_json.telemetry`.

## Rollback
- [ ] Set `MULTI_LLM_EXTRACTION_ENABLED=false` to disable multi-LLM candidate extraction; extraction continues with existing template/LLM fallback only.
- [ ] No schema change to document_uploads beyond optional `extraction_run_id`; existing flows unchanged when multi-LLM disabled.

## Regression
- [ ] Run regression suite: clean PDF, messy PDF, scanned PDF, negative numbers/sign swaps.
- [ ] At least one statement type (e.g. balance_sheet) runs end-to-end with multi-LLM and deterministic gating when enabled.
