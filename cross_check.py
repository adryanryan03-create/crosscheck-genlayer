# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Verdict:
    submitter: str
    claim: str
    url_a: str
    url_b: str
    support_a: bool
    support_b: bool
    corroborated: bool


class CrossCheck(gl.Contract):
    """
    CrossCheck verifies a claim against TWO independent web sources and
    stores the verdict only when GenLayer validator consensus agrees on
    how each source judges the claim.

    A single source can be wrong, edited, or taken out of context. Many
    real verification workflows (news fact-checking, event confirmation,
    market resolution) therefore require corroboration: the same claim
    confirmed by two independent publications. CrossCheck encodes that
    rule on-chain.

    verify_claim(claim, url_a, url_b): the leader fetches both pages and
    asks an LLM, for each page separately, whether that page directly
    supports the claim. Every validator independently repeats both
    fetches and both judgements, and the pair of boolean verdicts is
    accepted only when it matches exactly under the strict equivalence
    principle — the right check here, because the extracted values are
    booleans: two honest judgements of the same page against the same
    claim should agree, while a hallucinated or manipulated judgement
    diverges and fails consensus.

    The stored record keeps both per-source verdicts plus the combined
    result: corroborated is true only when BOTH sources support the
    claim. A claim backed by just one source is recorded as such —
    visible, auditable, and clearly not corroborated.
    """

    verdicts: TreeMap[str, Verdict]
    verdict_count: u256

    def __init__(self):
        self.verdict_count = u256(0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_url(self, url: str) -> str:
        cleaned = url.strip()
        if not (cleaned.startswith("https://") or cleaned.startswith("http://")):
            raise Exception("URL must start with http:// or https://")
        if len(cleaned) > 512:
            raise Exception("URL must be at most 512 characters")
        return cleaned

    def _fetch_page_text(self, url: str) -> str:
        # Runs inside the non-deterministic block: the leader fetches the
        # page, and each validator fetches it again independently.
        response = gl.nondet.web.get(url)
        return str(response)[:6000]

    def _judge_both_sources(self, claim: str, url_a: str, url_b: str) -> tuple:
        def run_judgement() -> str:
            results = {}
            for key, url in (("a", url_a), ("b", url_b)):
                page_text = self._fetch_page_text(url)
                task = f"""
Decide whether the web page content below directly supports the claim.

Claim:
{claim}

Web page content:
{page_text}

Respond in JSON:
{{
    "supported": bool // true only if the page content directly
                      // supports the claim, otherwise false
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Your output must be only JSON without any formatting
prefix or suffix, perfectly parsable by a JSON parser.
                """
                result = gl.exec_prompt(task).replace("```json", "").replace("```", "")
                parsed = json.loads(result)
                results[key] = bool(parsed.get("supported", False))
            return json.dumps(results, sort_keys=True)

        verdict = json.loads(gl.eq_principle_strict_eq(run_judgement))
        return bool(verdict.get("a", False)), bool(verdict.get("b", False))

    # ------------------------------------------------------------------
    # Public write methods
    # ------------------------------------------------------------------

    @gl.public.write
    def verify_claim(self, claim: str, url_a: str, url_b: str) -> None:
        clean_claim = claim.strip()
        if len(clean_claim) == 0:
            raise Exception("Claim must not be empty")
        if len(clean_claim) > 280:
            raise Exception("Claim must be at most 280 characters")
        clean_a = self._validate_url(url_a)
        clean_b = self._validate_url(url_b)
        if clean_a == clean_b:
            raise Exception("The two sources must be different URLs")

        support_a, support_b = self._judge_both_sources(clean_claim, clean_a, clean_b)

        verdict_id = str(int(self.verdict_count))
        self.verdicts[verdict_id] = Verdict(
            submitter=str(gl.message.sender_address),
            claim=clean_claim,
            url_a=clean_a,
            url_b=clean_b,
            support_a=support_a,
            support_b=support_b,
            corroborated=support_a and support_b,
        )
        self.verdict_count = u256(int(self.verdict_count) + 1)

    # ------------------------------------------------------------------
    # Public view methods
    # ------------------------------------------------------------------

    @gl.public.view
    def get_verdict(self, verdict_id: str) -> dict:
        if verdict_id not in self.verdicts:
            raise Exception("Verdict not found")
        verdict = self.verdicts[verdict_id]
        return {
            "submitter": verdict.submitter,
            "claim": verdict.claim,
            "url_a": verdict.url_a,
            "url_b": verdict.url_b,
            "support_a": verdict.support_a,
            "support_b": verdict.support_b,
            "corroborated": verdict.corroborated,
        }

    @gl.public.view
    def get_verdict_count(self) -> int:
        return int(self.verdict_count)
