"""M&A role resolution and financing structure engine (Item 10).

Resolves active and passive M&A syntax to identify:
- Acquirer (the entity taking on leverage / debt / integration risk)
- Target (the entity receiving takeover premium; not stressed)
- Financing structure (debt-financed x1.5, all-stock x0.5, baseline x1.0)
"""

import re
from typing import List, Optional, Tuple

from sentinel.contracts.signals import EntityReference, EvidenceSpan

ACTIVE_MA_VERBS = re.compile(
    r"\b(?:to\s+)?(?:acquire[sd]?|acquiring|buy(?:s|ing)?|bought|purchase[sd]?|purchasing|take\s+over|takes\s+over|took\s+over|taking\s+over)\b",
    re.I,
)
PASSIVE_MA_VERBS = re.compile(
    r"\b(?:to\s+be\s+|is\s+|was\s+|are\s+|were\s+)?(?:acquired|bought|purchased|taken\s+over)\s+by\b",
    re.I,
)

DEBT_FINANCING = re.compile(
    r"\b(bridge loan|debt[- ]financed|new notes|term loan|funded by (?:new )?debt|financed with (?:new )?debt|funded by debt|backed by (?:new )?debt)\b",
    re.I,
)
ALL_STOCK = re.compile(
    r"\b(all[- ]stock|stock[- ]for[- ]stock|all[- ]equity|funded by equity|funded with shares)\b",
    re.I,
)


def get_ma_financing_multiplier(text: str) -> float:
    """Return financing scale multiplier: 1.5 for debt-financed, 0.5 for all-stock, 1.0 baseline."""
    if DEBT_FINANCING.search(text):
        return 1.5
    if ALL_STOCK.search(text):
        return 0.5
    return 1.0


def resolve_ma_role_for_entity(
    text: str,
    entity_ref: EntityReference,
    entity_spans: List[EvidenceSpan],
) -> Tuple[str, Optional[EvidenceSpan]]:
    """Determine role of a resolved entity in M&A news: 'acquirer', 'target', or 'undetermined'.

    Rules:
    - If passive form ('X to be acquired by Y'): entity after 'by' is acquirer, before is target.
    - If active form ('Y to acquire X'): entity before verb is acquirer, after is target.
    - If neither syntax matches or roles cannot be disambiguated: 'undetermined'.
    """
    if not entity_spans:
        return "undetermined", None

    span_start = entity_spans[0].start
    span_end = entity_spans[0].end

    m_passive = PASSIVE_MA_VERBS.search(text)
    if m_passive:
        v_start = m_passive.start()
        v_end = m_passive.end()
        if span_start >= v_end:
            # Entity appears after passive verb -> acquirer
            return "acquirer", EvidenceSpan(start=v_start, end=v_end, text=text[v_start:v_end])
        elif span_end <= v_start:
            # Entity appears before passive verb -> target
            return "target", EvidenceSpan(start=v_start, end=v_end, text=text[v_start:v_end])
        return "undetermined", None

    m_active = ACTIVE_MA_VERBS.search(text)
    if m_active:
        v_start = m_active.start()
        v_end = m_active.end()
        if span_end <= v_start:
            # Entity appears before active verb -> acquirer
            return "acquirer", EvidenceSpan(start=v_start, end=v_end, text=text[v_start:v_end])
        elif span_start >= v_end:
            # Entity appears after active verb -> target
            return "target", EvidenceSpan(start=v_start, end=v_end, text=text[v_start:v_end])
        return "undetermined", None

    return "undetermined", None
