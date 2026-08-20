"""Applicant-facing explanation letters.

The boundary this module enforces
---------------------------------
The model decides. The language model only explains.

Reason codes are selected deterministically from SHAP attribution before this
module is invoked. Nothing here can change an outcome, alter a probability, or
choose which reasons are disclosed. The language model is handed a fixed set of
facts and asked to phrase them; it is a renderer, not a decision-maker.

That boundary is not stylistic. A generative model is non-deterministic, so a
system that let one select reason codes could produce two different legal
disclosures for the same applicant on two runs, and could not be audited. The
same request must always yield the same disclosed reasons.

Three controls
--------------
1. Redaction   -- the applicant's name never reaches the provider. The prompt
                  carries codes and figures only.
2. Validation  -- every number in the generated letter must appear in the
                  decision record. A letter inventing a figure is discarded.
3. Fallback    -- if no provider is configured, or generation fails, or the
                  validator rejects the output, a deterministic template is
                  used instead. The applicant always receives a letter, and it
                  is always accurate.

Configure a provider by setting LLM_PROVIDER and LLM_API_KEY in .env. With
LLM_PROVIDER=none the template path runs, which is a legitimate production
configuration rather than a degraded one.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import get_settings

# Numbers that may legitimately appear in a letter without being a claim about
# the applicant: list markers, and the year.
ALLOWED_INCIDENTAL = {"1", "2", "3", "4", "5", "2026"}

SYSTEM_PROMPT = """You write adverse action and approval notices for a regulated consumer lender.

Rules you must follow without exception:
- Use ONLY the facts supplied. Never introduce a number, percentage, amount,
  date or account detail that is not in the supplied facts.
- Never speculate about why a factor applies, and never suggest the decision
  could have been different.
- Do not mention models, algorithms, scores, machine learning or artificial
  intelligence.
- Address the reader as "you". Do not invent a name, address or reference.
- Plain, respectful, non-technical English. No marketing language. No apology.
- 120-170 words. Short paragraphs. No headings, no bullet points, no signature.

Structure: state the outcome, give the principal reasons in the order supplied,
state what may improve a future application, close with the right to request
further detail."""


@dataclass
class Explanation:
    letter: str
    source: str  # "llm" or "template"
    validated: bool
    prompt_hash: str | None
    rejection_reason: str | None = None


# ---------------------------------------------------------------------------
# Fact extraction and redaction
# ---------------------------------------------------------------------------

def build_facts(decision: dict[str, Any]) -> dict[str, Any]:
    """The only information a provider is given.

    The applicant's name, identifiers and raw feature values are excluded. A
    third-party endpoint receives an outcome, a set of reason statements and at
    most one monetary figure -- nothing that identifies a person.
    """
    reasons = decision.get("reasons") or []
    facts: dict[str, Any] = {
        "outcome": decision["outcome"],
        "principal_reasons": [
            {"statement": reason["statement"], "improvement": reason["improvement"]}
            for reason in reasons
        ],
    }
    if decision.get("outcome") == "APPROVE" and decision.get("approved_line"):
        facts["approved_credit_line_rupees"] = int(decision["approved_line"])
    return facts


def permitted_numbers(facts: dict[str, Any]) -> set[str]:
    """Every numeric token the letter is allowed to contain."""
    permitted = set(ALLOWED_INCIDENTAL)
    line = facts.get("approved_credit_line_rupees")
    if line is not None:
        permitted.add(str(line))
        # Accept grouped forms of the same figure, since a letter may render
        # 116700 as 1,16,700 or 116,700.
        permitted.add(f"{line:,}")
        permitted.add(_indian_grouping(str(line)))
    return permitted


def _indian_grouping(digits: str) -> str:
    """Format 116700 as 1,16,700."""
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_letter(letter: str, facts: dict[str, Any]) -> tuple[bool, str | None]:
    """Reject any letter asserting something the decision record does not say.

    The check is on numbers because that is where fabrication does concrete
    harm: an invented credit limit, interest rate or arrears figure is a false
    statement to a consumer about their own account.
    """
    permitted = permitted_numbers(facts)

    # Strip thousands separators so 1,16,700 is compared as one token.
    for token in re.findall(r"\d[\d,]*", letter):
        cleaned = token.rstrip(",")
        if cleaned in permitted or cleaned.replace(",", "") in {
            value.replace(",", "") for value in permitted
        }:
            continue
        return False, f"letter contains unsupported figure: {cleaned}"

    forbidden = ["algorithm", "model", "machine learning", "AI ", "artificial intelligence"]
    lowered = letter.lower()
    for term in forbidden:
        if term.lower() in lowered:
            return False, f"letter references internal machinery: {term.strip()}"

    if len(letter.split()) < 60:
        return False, "letter too short to constitute a disclosure"

    return True, None


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------

def template_letter(decision: dict[str, Any], facts: dict[str, Any]) -> str:
    """Compose the letter from the decision record alone.

    Correct by construction: every sentence is assembled from stored facts, so
    there is nothing to validate. This is the path taken whenever a provider is
    absent or its output is rejected.
    """
    reasons = facts["principal_reasons"]
    outcome = facts["outcome"]

    if outcome == "APPROVE":
        line = facts.get("approved_credit_line_rupees")
        opening = (
            f"We have approved your credit application"
            + (f", with a credit line of Rs {_indian_grouping(str(line))}." if line else ".")
        )
        middle = (
            "The following factors were the most significant in our assessment. "
            "They did not prevent approval, but they influenced the amount offered:"
            if reasons
            else "Your application met our criteria across all factors we assess."
        )
    else:
        verb = "declined" if outcome == "DECLINE" else "referred for further review"
        opening = f"We are unable to approve your application at this time; it has been {verb}."
        middle = "The principal reasons for this decision were:"

    body = "\n".join(f"- {reason['statement']}." for reason in reasons)
    improvements = "\n".join(f"- {reason['improvement']}" for reason in reasons)

    closing = (
        "You have the right to request further detail about this decision, and to "
        "ask us to review it if you believe the information we hold is incorrect. "
        "You may also request a copy of the information used in this assessment."
    )

    parts = [opening, "", middle]
    if body:
        parts += ["", body]
    if improvements:
        parts += ["", "What may help a future application:", "", improvements]
    parts += ["", closing]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _call_anthropic(prompt: str, settings) -> str:
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.llm_model or "claude-sonnet-4-6",
            "max_tokens": 600,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30.0,
    )
    response.raise_for_status()
    body = response.json()
    return "".join(
        block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"
    ).strip()


def _call_openai(prompt: str, settings) -> str:
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.llm_model or "gpt-4o-mini",
            "max_tokens": 600,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def _call_ollama(prompt: str, settings) -> str:
    """Locally hosted model. No key, no data leaving the machine."""
    response = httpx.post(
        "http://localhost:11434/api/chat",
        json={
            "model": settings.llm_model or "llama3.2",
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


PROVIDERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "ollama": _call_ollama,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def explain(decision: dict[str, Any]) -> Explanation:
    """Produce an applicant-facing letter for a decision."""
    settings = get_settings()
    facts = build_facts(decision)
    prompt = (
        "Write the notice using only these facts:\n\n"
        + json.dumps(facts, indent=2)
    )
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    provider = PROVIDERS.get(settings.llm_provider.lower())
    if provider is None or (
        settings.llm_provider.lower() != "ollama" and not settings.llm_api_key
    ):
        return Explanation(
            letter=template_letter(decision, facts),
            source="template",
            validated=True,
            prompt_hash=None,
        )

    try:
        letter = provider(prompt, settings)
    except Exception as exc:  # provider unreachable, rate limited, misconfigured
        return Explanation(
            letter=template_letter(decision, facts),
            source="template",
            validated=True,
            prompt_hash=prompt_hash,
            rejection_reason=f"provider unavailable: {type(exc).__name__}",
        )

    valid, problem = validate_letter(letter, facts)
    if not valid:
        # The generated text is discarded rather than shown with a warning. A
        # disclosure that may contain a fabricated figure is not fit to send.
        return Explanation(
            letter=template_letter(decision, facts),
            source="template",
            validated=False,
            prompt_hash=prompt_hash,
            rejection_reason=problem,
        )

    return Explanation(
        letter=letter, source="llm", validated=True, prompt_hash=prompt_hash
    )
