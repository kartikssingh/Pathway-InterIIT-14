"""Prompt templates.

Every prompt in the system used to be a multi-hundred-line string literal wedged
inside the function that called it — two of them were near-identical copies that
had already drifted apart.  Keeping them here means the scoring contract is
reviewable in one place and the flows stay readable.

The scoring algorithm the model is asked to follow is mirrored exactly by
:mod:`fraudguard.scoring`, which is used as the deterministic fallback when the
LLM is unavailable.
"""

from __future__ import annotations

from typing import Iterable, Sequence

__all__ = [
    "COMPLIANCE_SYSTEM_PROMPT",
    "ARTICLE_AUTHENTICITY_SYSTEM_PROMPT",
    "RPS_EXPLANATION_SYSTEM_PROMPT",
    "compliance_user_prompt",
    "article_authenticity_user_prompt",
    "watchdog_delta_prompt",
    "mcp_agent_prompt",
]


_SEVERITY_TABLE = """  * official_sanction   -> 1.00
  * conviction          -> 0.95
  * indictment/charges  -> 0.85
  * regulatory_fine     -> 0.70
  * credible_allegation -> 0.60
  * negative_media      -> 0.30
  * rumour              -> 0.10
  * other               -> 0.20"""

_OUTPUT_CONTRACT = """OUTPUT FORMAT (strict)
Produce exactly two sections, nothing else, with no extra commentary or fields:

```json
{"risk_score": <float 0..1 with 3 decimals>, "risk_classification": "<LOW|MEDIUM|HIGH|CRITICAL>", "match_found": <true|false>}
```
<SUMMARY>
One paragraph (single paragraph only) stating the numeric breakdown and the primary drivers. It must include:
- the parsed OpenSanctions count N and the resulting sanction_score,
- web_evidence_score and the number of contributing articles,
- match_confidence,
- the fusion formula used, the final rounded risk_score and its classification,
- the single strongest driver ("sanctions", "web evidence" or "match confidence"),
- any relevant entity context (e.g. high-risk nationality, occupation) supporting the assessment."""


COMPLIANCE_SYSTEM_PROMPT = f"""You are a compliance analyst LLM. Using the structured data below, compute a single normalised risk_score between 0 and 1, a risk_classification, and whether a match was found. Follow the algorithm and output rules exactly.

INPUT FIELDS
* Entity: string
* TopMatch: string — best OpenSanctions match name
* Score01: numeric match confidence in [0,1] (or a percentage — see parsing rules)
* WebNotes: rendered summary of scraped articles; each may carry a title, excerpt,
  authenticity score in [0,1], source, ISO date and a type drawn from
  ["official_sanction","conviction","indictment","regulatory_fine","credible_allegation","negative_media","rumour","other"]

ADDITIONAL ENTITY CONTEXT (for match validation and contextual assessment only)
* Annual Income, Occupation, Sources of Income, Marital Status, Nationality, Current Address

PARSING RULES
1. Parse Score01: if given as a percentage ("85%"), convert to 0.85. If >1 and <=100, divide by 100. If missing, default to 0.
2. Extract the OpenSanctions count N by parsing any integer from ScoreText. If none is found, set N = 0.
3. Clamp authenticity values to [0,1]. If there are no WebNotes, treat the list as empty.
4. Use the entity context to validate matches and add qualitative insight, but do NOT let it modify the computed scores.
5. Treat a null/None context field as "unknown" and ignore it entirely.

SCORE COMPONENTS
A. Sanctions component
   sanction_score = min(N / 5, 1.0)
   (5 or more confirmed sanctions is maximum sanctions risk; below that it scales linearly.)

B. Web evidence component
   For each article map its type (inferring from the excerpt when the type is absent) to a severity:
{_SEVERITY_TABLE}
   article_score = authenticity * article_severity, both in [0,1].
   Combine with a probabilistic union: web_evidence_score = 1 - prod(1 - article_score_i).
   With no articles, web_evidence_score = 0.

C. Match confidence
   match_confidence = parsed Score01, in [0,1].

FUSION
   final_risk_score = sanction_score * 0.60 + web_evidence_score * 0.30 + match_confidence * 0.10
   Round to 3 decimals and clamp to [0,1].

CLASSIFICATION
   LOW      0.000 <= score < 0.250
   MEDIUM   0.250 <= score < 0.500
   HIGH     0.500 <= score < 0.750
   CRITICAL          score >= 0.750

MATCH FOUND
   match_found = true when final_risk_score > 0, else false.

{_OUTPUT_CONTRACT}
"""


ARTICLE_AUTHENTICITY_SYSTEM_PROMPT = (
    "You are an expert news fact-checker and sentiment analyser. Analyse the provided "
    "article URL and text for journalistic quality, coherence and apparent authenticity. "
    "The source domain matters: an established publisher raises the score, an obscure or "
    "known-unreliable domain lowers it. Return an 'authenticity_score' between 0.0 "
    "(completely unreliable) and 1.0 (highly reliable, well-structured reporting) based on "
    "domain reputation, clarity of facts, named sources (e.g. CBI, ED, court rulings) and "
    "narrative structure. Output a single JSON object with the keys 'authenticity_score' "
    "(float) and 'reasoning' (string). Emit nothing outside the JSON block."
)


RPS_EXPLANATION_SYSTEM_PROMPT = (
    "You are a senior fraud risk analyst. You receive transaction features and the model "
    "scores p_ml, anomaly, evidence and rps. Your job is ONLY to interpret those scores and "
    "describe the risk. NEVER change a numeric score and never invent new numbers. Respond "
    "with STRICT JSON ONLY, containing exactly the keys: \"risk_level\" (string), "
    "\"short_reason\" (string), \"long_reason\" (string), \"recommended_action\" (string) and "
    "\"tags\" (array of strings). Add no other keys and do not wrap the JSON in markdown."
)


def compliance_user_prompt(
    *,
    name: str,
    top_match: str | None,
    score: float | str | None,
    web_notes: str,
    nationality: str | None = None,
    occupation: str | None = None,
    annual_income: str | None = None,
    marital_status: str | None = None,
    current_address: str | None = None,
    sources_of_income: Sequence[str] | None = None,
    address_limit: int = 100,
) -> str:
    """Render the per-entity half of the compliance prompt."""
    address = (current_address or "")[:address_limit] or "Unknown"
    income_sources = ", ".join(sources_of_income) if sources_of_income else "Unknown"
    return (
        "Analyse the following entity information and produce the risk_score and "
        "risk_classification according to the rules above.\n\n"
        f"Entity: {name}\n"
        f"TopMatch: {top_match or 'None'}\n"
        f"Score01: {score if score is not None else 0}\n"
        "Entity Context — "
        f"Nationality: {nationality or 'Unknown'}, "
        f"Occupation: {occupation or 'Unknown'}, "
        f"Annual Income: {annual_income or 'Unknown'}, "
        f"Marital Status: {marital_status or 'Unknown'}, "
        f"Address: {address}, "
        f"Income Sources: {income_sources}\n\n"
        f"WebNotes: {web_notes}\n"
    )


def article_authenticity_user_prompt(
    *,
    url: str,
    text: str,
    alexa_rank: str = "unknown",
    akamai_rank: str = "unknown",
    content_signal_score: float = 0.0,
    has_domain_history: bool = False,
) -> str:
    return (
        "Analyse the following article and provide an authenticity score per the system "
        "instructions.\n\n"
        f"**ARTICLE URL:** {url}\n\n"
        f"**ARTICLE TEXT:**\n{text}\n\n"
        "--- ADDITIONAL AUTHENTICITY CONTEXT ---\n"
        "Use these indicators to adjust the final score:\n"
        f"- **Reputation (AlienVault):** Alexa rank {alexa_rank} / Akamai rank {akamai_rank}\n"
        "  *(A prominent rank raises the score; 'unknown' or a very high rank lowers it.)*\n"
        f"- **Content signals score:** {content_signal_score:.2f}\n"
        "  *(Presence of author, date, outbound links and schema markup — higher is better hygiene.)*\n"
        f"- **Domain has archive history (Wayback):** {has_domain_history}\n"
        "  *(A domain with history is less likely to be a fly-by-night misinformation site.)*\n"
    )


def watchdog_delta_prompt(
    *, entity_id: str, name: str, previous_rps: float, old_notes: str, new_notes: str
) -> str:
    """Prompt used when adverse-media coverage for a known entity has shifted.

    Extends the compliance contract with a deterministic rho-0 update rule so a
    re-screen can only move the score by the *change* in web evidence.
    """
    return f"""{COMPLIANCE_SYSTEM_PROMPT}

WEB ANALYSIS CHANGE HANDLING (rho0 update)
* Purpose: when a previous and a current web analysis are both supplied, update rho0
  deterministically from the change in web evidence between them.
* Compute web_evidence_score_old from the OLD notes and web_evidence_score_new from the NEW
  notes, applying exactly the severity mapping and probabilistic union defined above.
* delta_web = web_evidence_score_new - web_evidence_score_old
* rho0_new = clamp(PreviousRho0 + delta_web, 0.0, 1.0)
* If only NEW notes exist, treat web_evidence_score_old as 0.0.
* If PreviousRho0 is absent, do not infer one — skip the rho0 update entirely.
* rho0_new feeds downstream systems only; it does not alter the fusion weights above.

Analyse the following entity and report the updated risk:

EntityID: {entity_id}
Entity: {name}
PreviousRho0: {previous_rps}

PREVIOUS WEB NOTES:
{old_notes}

CURRENT WEB NOTES:
{new_notes}
"""


def mcp_agent_prompt(
    *,
    full_name: str,
    risk_level: str,
    anomaly: float,
    rps: float,
    p_ml: float,
    evidence: float,
    tags: Iterable[str] | str,
    short_reason: str,
    long_reason: str,
    recommended_action: str,
) -> str:
    """Task given to the CrewAI agent that decides which MCP tools to call."""
    rendered_tags = tags if isinstance(tags, str) else ", ".join(tags)
    return f"""You are an expert Financial Crime Risk Analyst.
Your goal is to validate the risk propensity score (RPS) for the entity below.

### TRANSACTION METADATA
- **Entity (name)**: {full_name}
- **Risk Level**: {risk_level}
- **Scores**: anomaly={anomaly:.2f}, rps={rps:.2f}, p_ml={p_ml:.2f}, evidence={evidence:.4f}
- **Tags**: {rendered_tags}

### ANALYSIS CONTEXT
**Short summary**: {short_reason}
**Detailed analysis**: {long_reason}
**System recommendation**: {recommended_action}

### YOUR TASK
You have access to these validation tools:
1. `ofac_call` — checks global OFAC sanctions for a name.
2. `pep_call`  — checks Politically Exposed Person status for a name.

Decide whether the combination of the anomaly score, the entity's identity and the RPS
justification warrants a tool call.
- If YES: call the tool(s) needed to verify the specific risks you see, then summarise
  what they returned and whether they support or contradict the score.
- If NO: state your validation from the supplied evidence alone, and say why no external
  check was required.
Keep the answer under 200 words and end with a single line
`VERDICT: <CONFIRMED|REJECTED|INCONCLUSIVE>`.
"""
