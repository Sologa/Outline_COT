# Runbook

Credential source for this smoke test:

```bash
/Users/xjp/Desktop/NLP_PRISMA_Reviews/.env
```

The runner reads the key at execution time and does not copy it into this repository.

## Tests

```bash
python3 -m unittest engineering_validation/2026-05-21_api_generation_smoke/tests/test_api_generation_smoke.py
```

## Render Only

```bash
python3 engineering_validation/2026-05-21_api_generation_smoke/prototype/run_api_generation_smoke.py \
  --mode render
```

## Async API Smoke

```bash
python3 engineering_validation/2026-05-21_api_generation_smoke/prototype/run_api_generation_smoke.py \
  --mode async \
  --env-file /Users/xjp/Desktop/NLP_PRISMA_Reviews/.env \
  --force
```

## Batch API Smoke

```bash
python3 engineering_validation/2026-05-21_api_generation_smoke/prototype/run_api_generation_smoke.py \
  --mode batch \
  --env-file /Users/xjp/Desktop/NLP_PRISMA_Reviews/.env \
  --force
```

## Both Modes

```bash
python3 engineering_validation/2026-05-21_api_generation_smoke/prototype/run_api_generation_smoke.py \
  --mode both \
  --env-file /Users/xjp/Desktop/NLP_PRISMA_Reviews/.env \
  --force
```

## Usage And Cost Backfill

If `response.json` files already exist, rerun without `--force` to backfill accounting without making new API calls:

```bash
python3 engineering_validation/2026-05-21_api_generation_smoke/prototype/run_api_generation_smoke.py \
  --mode both
```

This writes per-mode `usage_and_cost.json`, updates `run_manifest.json`, and rebuilds aggregate `usage_summary.json` / `usage_summary.csv`.
Fresh API runs also print a one-line terminal accounting summary such as `[usage] async tokens=... estimated_cost_usd=$...`.
