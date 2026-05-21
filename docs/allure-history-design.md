# Allure Report History — Design & Findings

## Overview

`run_allure.py` is a local orchestration script that simulates multiple CI runs back-to-back so that Allure Report 3's **trend** and **history** widgets populate correctly without waiting for real pipeline executions.

---

## How Allure v3 History Works

Allure 3 tracks cross-run history through a **JSONL ledger file** (one JSON object per line, one line per `allure generate` call).

Relevant `allurerc.yml` options ([Allure 3 configuration reference](https://allurereport.org/docs/v3/configure/)):

| Option          | Value                            | Effect                                                               |
|-----------------|----------------------------------|----------------------------------------------------------------------|
| `historyPath`   | `./.allure/allure-history.jsonl` | Path to the persistent history ledger                                |
| `appendHistory` | `true`                           | Each `allure generate` **appends** a new line instead of overwriting |
| `output`        | `./allure-report`                | Where the generated static report is written                         |

Each line written to the JSONL file has this shape:

---

## Script Logic (`run_allure.py`)

```
runs = 3
history_limit = 2

clean_environment()          # wipe allure-results/, allure-report/, reset JSONL
│
└─ for i in range(runs):                 # simulate multiple runs
     │
     ├─ rmtree(allure-results/)    # prevent double-counting from prior run
     ├─ rmtree(allure-report/)     # ⚠️ CRITICAL — see "Root Cause" below
     │
     ├─ pytest --alluredir=allure-results   # produce raw result JSON files
     │
     └─ allure generate --config allurerc.yml --history-limit history_limit
            │
            ├─ reads allure-results/       (current run data)
            ├─ reads .allure/allure-history.jsonl  (prior runs)
            ├─ appends new line to JSONL   (appendHistory: true)
            └─ writes static report → allure-report/
```

`--history-limit 2` caps how many previous runs are retained in trend charts.
Ive observed some inconsistencies in how this limit is applied, but it does not affect the core behavior of the tool.

---

## Issue: Generate report has is not integrating history

**Symptom**: When running `run_allure.py`, the first run correctly shows 108 tests as brand-new. However, the second run also shows all 108 tests as brand-new instead of recognizing them as historical. All historical data although collected correctly in the JSONL file is not reflected in the generated report.

**Root cause**: The `allure-report/` output directory was **not deleted** between runs.

When `allure generate` writes a report into an existing `allure-report/` directory, it merges/overwrites individual files but the stale report metadata can cause the new report to reference the wrong history snapshot. Because both generate calls targeted the same output directory without clearing it first, Run #2's report rendered as if it had no prior history even though the JSONL file was correctly appended.

**Fix**: Delete `allure-report/` before **each** `allure generate` call, not only during the initial `clean_environment()` step.

```python
if os.path.exists(REPORT_DIR):
    shutil.rmtree(REPORT_DIR)
```

This ensures every `allure generate` writes into a clean output directory and correctly incorporates all prior lines from the JSONL ledger.

---

## Key Takeaways

- **`allure-results/`** must be cleared before each `pytest` run to avoid mixing result files from different runs.
- **`allure-report/`** must be cleared before each `allure generate` call to prevent stale report artifacts from masking history data.
- **`.allure/allure-history.jsonl`** should only be reset once at the start of the benchmark loop — it is the durable cross-run record and must persist across all `allure generate` invocations.
- The JSONL file grows by one line per `allure generate` call. Each line is a complete snapshot of that run's test results, keyed by `historyId`.
