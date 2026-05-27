# Runbook

This probe writes only under:

`results/experiments/2026-05-26_taxoadapt_blind_adaptive_two_paper_probe/`

## Render

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_taxoadapt_blind_adaptive_two_paper_probe/prototype/run_taxoadapt_blind_adaptive_payload_batch.py \
  --render-only \
  --write-batch-input
```

Expected request count: `4`.

## Submit And Collect Batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_taxoadapt_blind_adaptive_two_paper_probe/prototype/run_taxoadapt_blind_adaptive_payload_batch.py \
  --write-batch-input \
  --submit-only

PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_taxoadapt_blind_adaptive_two_paper_probe/prototype/run_taxoadapt_blind_adaptive_payload_batch.py \
  --batch-id <batch_id> \
  --max-wait-secs -1 \
  --poll-interval-secs 30
```

## Evaluate

```bash
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-05-26_taxoadapt_blind_adaptive_two_paper_probe/prototype/evaluate_taxoadapt_blind_adaptive_payload.py
```
