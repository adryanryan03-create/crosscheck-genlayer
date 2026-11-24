# CrossCheck — Test Plan (GenLayer Studio / StudioNet)

## Setup

1. Open GenLayer Studio (studio.genlayer.com), create or select an
   account with StudioNet GEN.
2. Upload `cross_check.py` (keep the runner header on line 1 intact)
   and deploy it. The constructor takes no arguments.
3. Note the contract address and confirm the deployment reaches
   Accepted / Finalized.

## Happy path — corroborated claim

1. Pick a factual claim and two independent public pages that both
   state it (e.g., two different news/docs pages about the same event).
2. Call `verify_claim(claim, url_a, url_b)`.
3. Expected: the transaction finalizes; `get_verdict_count()` returns 1.
4. Call `get_verdict("0")`.
   Expected: `support_a: true`, `support_b: true`,
   `corroborated: true`, and the stored claim/URLs match the inputs.

## Single-source support — stored, not corroborated

1. Pick a claim that only the first page states; the second page does
   not mention it.
2. Call `verify_claim(claim, url_a, url_b)`.
3. Expected: the transaction finalizes and stores the record with
   `support_a: true`, `support_b: false`, `corroborated: false`.
   The contract must NOT revert — a split verdict is a valid result.

## Unsupported claim

1. Pick a claim neither page supports.
2. Call `verify_claim(claim, url_a, url_b)`.
3. Expected: record stored with both verdicts `false` and
   `corroborated: false`.

## Failure cases (must revert)

| Case | Input | Expected |
| --- | --- | --- |
| Same source twice | `url_a == url_b` | Revert: "The two sources must be different URLs" |
| Bad scheme | URL without `http://` / `https://` | Revert: URL validation error |
| Overlong URL | URL longer than 512 chars | Revert: URL validation error |
| Empty claim | `claim = ""` | Revert: "Claim must not be empty" |
| Overlong claim | Claim longer than 280 chars | Revert: "Claim must be at most 280 characters" |
| Unknown id | `get_verdict("999")` | Revert: "Verdict not found" |

## Consensus behaviour to observe

- In the Studio transactions panel, confirm validators independently
  run both page fetches and both judgements (Leader/Validator tabs).
- If a page changes between leader and validator fetches so the
  boolean verdicts diverge, the transaction should fail consensus
  rather than store a contested verdict.
