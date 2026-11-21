# Same Person or Not?

Group workspace for the name-screening challenge. Each alert is a customer who might match one or more watchlist profiles. For every hit, decide whether it is the same person or company.

This checkout holds the browsable development set as one CSV per workbook sheet. The challenge text says the JSON Lines files in `dev/` are the scoring format. Those files are not in this repo yet. `data/` is the copy we load and test against.

## Setup

The project environment is `.Hack_venv`, created with Python 3.14. It stays on your machine. Python 3.11 or newer is enough to run the package.

```bash
python3 -m venv .Hack_venv
source .Hack_venv/bin/activate
python -m pip install -e ".[dev]"
```

If the environment already exists, the install line is the one you need. `make install` does the same thing against `.Hack_venv`.

```bash
python -m same_person
```

That prints a row count for every file in `data/`.

```python
from same_person import Table, load_table, load_text

alerts = load_table(Table.ALERTS)
policy = load_text(Table.POLICY)
```

Cells are strings. An empty cell is `""`. The token `NA` stays `NA`, because the SOP treats it as a name placeholder rather than a missing value.

## Layout

```text
data/                 one CSV per workbook sheet
src/same_person/      installable package
  catalog.py          file names, columns, and keys
  load.py             CSV readers
  decisions.py        decision and reason-code vocabulary
  export.py           rebuild the CSVs from the .xlsx workbook
tests/                contract tests against data/ and small fixtures
.github/workflows/    lint and tests on pull requests
```

`src/same_person/catalog.py` is the contract. The loader rejects a file whose header has drifted, and CI runs that check.

## Data

| File | Rows | Key | What it is |
| --- | ---: | --- | --- |
| `Start_here.csv` | 27 | | How the sheets fit together |
| `Alerts.csv` | 440 | `alert_id` | Customer as screened, plus hit ids |
| `Hits.csv` | 819 | `hit_id` | Watchlist profile that matched |
| `Customers.csv` | 72,265 | `record_id` | System of record |
| `Accounts.csv` | 86,659 | `account_id`, `customer_id` | Logins and account numbers. Joint accounts share an account id |
| `Onboarding.csv` | 72,265 | `account_id`, `customer_id` | Account to KYC applicant |
| `KYC_checks.csv` | 54,488 | `check_id` | Identity checks, keyed by applicant |
| `Notes.csv` | 31,895 | `note_id` | Notes filed by customer email |
| `Search_results.csv` | 16,882 | `result_id` | Web results for a name. Most are namesakes |
| `Practice_labels.csv` | 50 | `hit_id` | Answered hits and the path to the answer |
| `Policy.csv` | 117 | | The identity SOP and the name-variant groups |

Joins, from the orientation sheet:

- `Alerts.hit_ids` → `Hits.hit_id`
- `Alerts.account_ref` → `Accounts.account_id` → `Accounts.customer_id` → `Customers.record_id`
- `Alerts.login_handle` → `Accounts.login_handle` → `Customers.record_id`
- `Alerts.email` → `Customers.email`
- `Accounts.account_id` + `customer_id` → `Onboarding` → `kyc_applicant_id` → `KYC_checks.applicant_id`
- `Customers.email` → `Notes.requester_email`
- Hit name → `Search_results.query` (the name's lowercase words in alphabetical order)

`Practice_labels.csv` is the only file with answers. An alert is cleared only when every hit on it is `DIFFERENT_ENTITY`.

To rebuild `data/` from the browse workbook:

```bash
python -m same_person.export "Screening Dev Set - browse.xlsx"
```

That overwrites `data/`. Pass `--out` to write somewhere else. The workbook's sheet names and headers have to match the catalog.

## Decisions

`Decision` is `SAME_ENTITY`, `DIFFERENT_ENTITY`, or `REVIEW`. `ReasonCode` lists the codes in the SOP, and each code belongs to one decision. `parse_reason_codes` splits the semicolon-separated cell used in the practice labels.

## Screener

`same_person.screener` decides every hit and builds a dashboard. It follows the review pipeline step by step and applies the SOP in `Policy.csv` to decide.

```powershell
.Hack_venv\Scripts\python.exe -m same_person.screener
```

It takes about 15 seconds and writes to `outputs/screener/`:

| File | What it is |
| --- | --- |
| `dashboard.html` | Open in a browser. Filter by decision, red flags or practice labels; click a row for the trail and every flag |
| `screener_results.csv` | One row per hit: decision, reason codes, rating, red flags, explanation, path |
| `decisions.jsonl` | Decision, reason codes, `customer_record_id` and cited evidence per hit |
| `label_score.json` | Accuracy against `Practice_labels.csv` and any wrong hits |

Pipeline, per hit, with the red flags each step raises:

1. **Alert against hit.** The hit must be listed on its alert, and `hit_count` must match. The practice label is attached when there is one.
2. **Intrinsic characteristics.** The screened name, date of birth, country and city are scored against the hit using the existing `score_matches.py` baseline, which gives a step-2 score from 0 to 100.
3. **Accounts.** `account_ref` or `login_handle` (or `email`, or a search by name, date of birth, country and city when there is no link) leads into Accounts. Flags: joint holders, several accounts, several login handles, and another login on the same phone opened the same day.
4. **Onboarding.** The account and customer lead to the KYC applicant.
5. **KYC.** The latest approved check (KYC provider or KYC note) gives the verified name, date of birth and document country. Flags: a different date of birth or name across approved checks, rejected or expired checks, a verified date of birth or name that differs from the record, and a screened date of birth that differs.
6. **Joint and linked records.** Every holder of a joint account is compared by date of birth, nationality, address, email and phone. Records that share a phone and full date of birth, or a document number, are one person, and any differences between them are flagged.

The decision follows the SOP. A hit is cleared only on a contradiction (time, date of birth, location, verified name, type, death) and confirmed only on agreement. Anything else is `REVIEW`. If several people fit and they lead to different decisions, the hit is `REVIEW` with `AMBIGUOUS_CUSTOMER_RECORD`.

The screener leans to `REVIEW`. A clearance is held for review when a high red flag casts doubt on the fact that cleared it, for example a date-of-birth mismatch on a customer whose approved checks disagree on their date of birth. It is also held when another identity on the same phone and opening date would not be cleared. Pass `--strict-sop` to turn this off.

The **rating** runs from 0 to 100, and higher means more likely the same entity. The decision sets the band: SAME is 80 to 100, REVIEW is 40 to 79, and DIFFERENT is 0 to 39. Within a band, the step-2 score and the number of agreeing facts set the value.

## Development

```bash
make check
```

`make check` lints with Ruff and runs the tests. `make format` applies the formatter. The tests confirm headers, unique keys, and that every practice label uses a reason code allowed for its decision.

Do not commit `.Hack_venv`. The root `.gitignore` excludes it, along with caches and `.env` files.
