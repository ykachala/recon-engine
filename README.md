# recon-engine

**Transaction reconciliation service — ~2,400 records/sec single-worker throughput. Matches, flags, and reports discrepancies between uploaded transaction exports and reference datasets.**

| Metric | Result |
|--------|--------|
| Throughput (single Celery worker) | **~2,400 records/sec** |
| Match strategies | Exact + fuzzy (amount tolerance, date window, description similarity) |
| Discrepancy types | Amount mismatch, missing in source, missing in reference, duplicate |
| Idempotent runs | Same run ID returns cached result |

*Benchmark: `python scripts/benchmark.py 5000` against synthetic ZAR transaction fixtures on a single worker. Actual throughput varies with database write latency.*

![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django_5-092E20?style=flat&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-ff1709?style=flat)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-2088FF?style=flat&logo=github-actions&logoColor=white)

---

## What this is

Recon Engine is a backend service that reconciles two sets of financial transaction records — an uploaded export (from a billing system, payment gateway, or bank feed) against a reference dataset. It matches transactions by exact amount/date, fuzzy-matches near-misses within configurable tolerances, and surfaces discrepancies with enough detail to act on.

Built from hands-on experience with subscription billing at FlexClub and web hosting billing at 1-Grid, where transaction reconciliation was a recurring operational problem: amounts off by rounding, dates shifted by one day, reference IDs that don't align across systems.

---

## Architecture

```
Client
  │
  │  POST /api/v1/runs/  (source_file + reference_file paths)
  ▼
┌────────────────────────────────────────────┐
│              Django REST API                │
│  - Validates request                        │
│  - Creates ReconciliationRun (status=pending)│
│  - Enqueues Celery task                     │
│  - Returns 202 + run_id                    │
└────────────────────┬───────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────┐
│              Celery Worker                  │
│                                            │
│  1. Parse source CSV → Transaction rows    │
│  2. Parse reference CSV → Transaction rows │
│  3. For each source txn:                  │
│     a. Try exact match (amount+date+ccy)   │
│     b. Try fuzzy match (tolerance window)  │
│     c. If no match → MISSING_IN_REFERENCE  │
│  4. Flag unmatched reference rows →        │
│     MISSING_IN_SOURCE                      │
│  5. Bulk-insert Discrepancy records        │
│  6. Update run status → complete           │
└────────────────────┬───────────────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
         PostgreSQL        Redis
         (run records,    (Celery broker
          transactions,    + result backend)
          discrepancies)
```

---

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Runtime | Python 3.12 | Full async support, strong typing |
| Framework | Django 5 + DRF | Mature ORM, built-in admin, DRF pagination |
| Task queue | Celery 5 + Redis | Async processing; retry on failure |
| Database | PostgreSQL 16 | Bulk insert, indexed amount/date queries |
| Matching | fuzzywuzzy + Levenshtein | Description similarity scoring |
| Containerisation | Docker + Docker Compose | Local stack in one command |
| CI/CD | GitHub Actions | ruff → mypy → pytest on every push |

---

## Matching strategy

Three-pass match for each source transaction:

1. **Exact match** — same `amount_cents`, `date`, and `currency`. Confidence 1.0.
2. **Fuzzy match** — `amount_cents` within `RECON_AMOUNT_TOLERANCE_CENTS`, date within `RECON_DATE_TOLERANCE_DAYS`, description similarity above `RECON_FUZZY_DESCRIPTION_THRESHOLD` (fuzz.token_sort_ratio). Confidence proportional to amount delta.
3. **No match** — flagged as `MISSING_IN_REFERENCE`.

Reference transactions not matched to any source row are flagged as `MISSING_IN_SOURCE`.

Amount mismatches (fuzzy matches with non-zero delta) are flagged as `AMOUNT_MISMATCH` with the `delta_cents` recorded.

---

## API

```
POST   /api/v1/runs/                        # Submit reconciliation run (async)
GET    /api/v1/runs/                        # List runs
GET    /api/v1/runs/:id/                    # Run detail + counts
GET    /api/v1/runs/:id/discrepancies/      # List discrepancies (filterable by kind)
```

### Example

```bash
# Start a reconciliation run
curl -X POST http://localhost:8000/api/v1/runs/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "March 2025 billing reconciliation",
    "source_file": "/data/uploads/march_billing.csv",
    "reference_file": "/data/uploads/march_bank_export.csv"
  }'

# Response: 202 Accepted
# { "id": "...", "status": "pending", "matched_count": 0, ... }

# Poll for result
curl http://localhost:8000/api/v1/runs/<id>/

# Get discrepancies (amount mismatches only)
curl "http://localhost:8000/api/v1/runs/<id>/discrepancies/?kind=amount_mismatch"
```

### CSV format

The parser understands common field aliases:
- Date: `date`, `transaction_date`, `txn_date`, `value_date`
- Description: `description`, `narration`, `details`, `reference`, `memo`
- Amount: `amount`, `debit`, `credit`, `value`, `amount_zar`

Date formats supported: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY/MM/DD`.
Amounts: comma-separated thousands handled (`45,000.00` → 4,500,000 cents).

---

## Getting started

```bash
git clone https://github.com/ykachala/recon-engine.git
cd recon-engine
cp .env.example .env
docker compose up
```

API: `http://localhost:8000`

```bash
# Run tests
pip install -e ".[dev]"
pytest tests/

# Run with coverage
pytest tests/ --cov=recon --cov-report=html

# Run benchmark
python scripts/benchmark.py 5000
```

### Environment variables

```env
SECRET_KEY=...
DB_NAME=recon
DB_USER=recon
DB_PASSWORD=recon
DB_HOST=db
REDIS_URL=redis://redis:6379/0

RECON_AMOUNT_TOLERANCE_CENTS=0       # 0 = exact match only
RECON_DATE_TOLERANCE_DAYS=1          # ±1 day for fuzzy matching
RECON_FUZZY_DESCRIPTION_THRESHOLD=80 # fuzzywuzzy score 0–100
```

---

## Project structure

```
recon-engine/
├── recon/
│   ├── models.py       # ReconciliationRun, Transaction, Discrepancy
│   ├── tasks.py        # Celery async reconciliation pipeline
│   ├── matchers.py     # exact, fuzzy amount, find_best_match
│   ├── parsers.py      # CSV parsing with field alias resolution
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── config/
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── tests/
│   ├── unit/           # test_matchers.py, test_parsers.py
│   └── integration/    # test_api.py
├── scripts/
│   └── benchmark.py    # throughput benchmark
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .github/workflows/ci.yml
```

---

## Related

- [finparse-ai](https://github.com/ykachala/finparse-ai) — extracts structured transaction data from financial documents; output is a natural input to this reconciliation pipeline
- [billing-worker](https://github.com/ykachala/billing-worker) — the Celery-based billing processor this was designed to reconcile against

---

**Author:** Yoweli Kachala &nbsp;|&nbsp; [LinkedIn](https://linkedin.com/in/yoweli-kachala) &nbsp;|&nbsp; Cape Town, South Africa  
*Built from billing reconciliation work at FlexClub and 1-Grid — systems where a 50-cent rounding error multiplied by 10,000 transactions matters.*
