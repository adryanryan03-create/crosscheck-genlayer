# CrossCheck — Two-Source Claim Corroboration by Consensus

CrossCheck is a GenLayer Intelligent Contract that verifies a claim
against **two independent web sources** and records the verdict
on-chain only after validator consensus agrees on how each source
judges the claim.

A single source can be wrong, silently edited, or quoted out of
context. Serious verification workflows — news fact-checking, event
confirmation, prediction-market resolution — therefore ask for
**corroboration**: the same claim confirmed independently by two
different publications. CrossCheck encodes that rule as a contract.

## Live deployment (StudioNet)

CrossCheck is deployed and finalized on GenLayer StudioNet:

- **Contract:** `0x37D56fBd44ef4965d6059d0039393fC3800d50AF`
- **Explorer:** https://explorer-studio.genlayer.com/address/0x37D56fBd44ef4965d6059d0039393fC3800d50AF
- **Deploy tx:** `0x5bf12bb533789aed6a9de86aeaa88d46a0b331a96e484de280dec8f2fc4bd45a`
- Deployed from GenLayer Studio; write method `verify_claim` and read
  methods `get_verdict`, `get_verdict_count` are live.

## How it works

`verify_claim(claim, url_a, url_b)`:

1. The **leader** fetches both pages (`gl.nondet.web.get`) and asks an
   LLM, for each page separately, whether that page directly supports
   the claim (`gl.exec_prompt`).
2. Every **validator** independently repeats both fetches and both
   judgements.
3. The pair of boolean verdicts is accepted only if it matches exactly
   under the **strict equivalence principle**
   (`gl.eq_principle_strict_eq`). Booleans are the ideal input for
   strict equality: two honest judgements of the same page against the
   same claim should agree, while a hallucinated or manipulated
   judgement diverges and fails consensus.

The stored record keeps **both per-source verdicts** plus the combined
result: `corroborated` is `true` only when **both** sources support the
claim. A claim backed by only one source is stored as exactly that —
visible and auditable, never silently upgraded.

## How this differs from a single-source checker

- **One fetch, one opinion** is a single point of failure: one edited
  page flips the result.
- CrossCheck requires **two independent publications** to agree before
  a claim counts as corroborated, and it preserves the split verdict
  (`support_a`, `support_b`) so downstream contracts and readers can
  apply their own policy (require both, accept either, weight sources).

## Contract API

State: one `TreeMap` store with sequential ids — `verdicts` — each
record keeping the submitter address, the claim, both source URLs, and
the three verdict fields.

| Method | Type | Description |
| --- | --- | --- |
| `verify_claim(claim, url_a, url_b)` | write | Judge `claim` against both pages; store per-source verdicts and the corroboration result if consensus agrees. |
| `get_verdict(verdict_id)` | view | Return `{submitter, claim, url_a, url_b, support_a, support_b, corroborated}` for a stored verdict. |
| `get_verdict_count()` | view | Number of stored verdicts. |

Input rules: both URLs must start with `http://` or `https://` (max
512 chars) and must differ from each other; claims max 280 chars. Page
content is truncated to the first 6,000 characters before judgement.

## Example session (GenLayer Studio / StudioNet)

1. Deploy `cross_check.py` (runner header on line 1 selects the
   `py-genlayer` runner — keep it intact).
2. Verify a claim against two reports of the same event:
   `verify_claim("The GenLayer airdrop snapshot was taken on 25 October 2026", "<news article URL>", "<second article URL>")`
   → after consensus, `get_verdict("0")` returns both per-source
   verdicts and whether the claim is corroborated.

See `TESTING.md` for a fuller test walkthrough, including the failure
cases (same URL twice → revert; one source silent on the claim →
stored with `corroborated: false`).

## Limitations

- Pages behind logins, paywalls, or heavy JavaScript may not return
  their visible content to a plain fetch; a source that cannot be read
  cannot support a claim and is judged accordingly.
- Corroboration is only as independent as the two URLs chosen — two
  pages copying the same wire report are weaker evidence than two
  original reports. The contract records the URLs so readers can judge
  independence themselves.
- Claims must be checkable against page text; opinion or prediction
  claims are out of scope by design.

## Files

- `cross_check.py` — the Intelligent Contract (single file, no
  dependencies beyond the GenLayer Python SDK).
- `TESTING.md` — manual test plan for Studio/StudioNet.
- `README.md` — this document.
