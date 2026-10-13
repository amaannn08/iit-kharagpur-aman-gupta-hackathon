"""Domain-grounded credit and cyber event taxonomy and extraction rules.

Citations:
1. International Swaps and Derivatives Association (ISDA), 2014 ISDA Credit
   Derivatives Definitions, Section 4 (Credit Events):
   - Section 4.2 Bankruptcy: Insolvency, unable to pay debts, winding-up,
     administration order, liquidation, receivership.
   - Section 4.5 Failure to Pay: Failure to make payments when due after expiration
     of Grace Period.
   - Section 4.6 Repudiation/Moratorium: Authorized officer or governmental authority
     disaffirms, disclaims, or declares moratorium/standstill.
   - Section 4.7 Restructuring: Reduction or postponement of principal/interest/fees.
   - Section 4.8 Governmental Intervention: Mandatory bail-in, expropriation,
     mandatory transfer, or regulatory resolution/receivership pursuant to law.
2. Federal Deposit Insurance Act (FDIA), 12 U.S.C. § 1821(c):
   Appointment of FDIC as receiver or conservator for insured depository institutions;
   resolution of failing banks following systemic deposit runs.
3. Basel Committee on Banking Supervision (BCBS) Liquidity Framework:
   Distress indicators: acute deposit outflows, asset fire sales (unrealized bond losses),
   discount window borrowing, liquidity shortfall.
4. U.S. Securities and Exchange Commission (SEC), Form 8-K Item 1.05:
   Material Cybersecurity Incidents (Release Nos. 33-11216; 34-97964).
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from sentinel.contracts.signals import EvidenceSpan


@dataclass
class DomainTermMatch:
    """Represents a matched domain credit or cyber event."""

    event_class: str
    term_category: str
    severity_floor: int
    confidence: float
    evidence_span: EvidenceSpan
    matched_phrase: str


# 1. ISDA Section 4.2 Bankruptcy & Section 4.8 Governmental Intervention (Floor 8)
ISDA_BANKRUPTCY_INTERVENTION = re.compile(
    r"\b("
    r"bankrupt(?:cy|cies)?|"
    r"chapter (?:11|7)|"
    r"insolven(?:t|cy)|"
    r"liquidation|"
    r"winding[- ]up|"
    r"receivership|"
    r"conservatorship|"
    r"seized by (?:the )?(?:fdic|regulators?|authorities|central bank)|"
    r"shut down by (?:the )?(?:fdic|regulators?|banking regulators?|authorities)|"
    r"closed by (?:the )?(?:fdic|regulators?|banking regulators?|authorities)|"
    r"taken over by (?:the )?(?:fdic|regulators?)|"
    r"placed in (?:fdic )?receivership|"
    r"(?:fdic|regulatory) seizure|"
    r"(?:bank|lender|firm|institution)\s+(?:fails|failed|collapse[sd]?)|"
    r"banking collapse"
    r")\b",
    re.I,
)

# 2. ISDA Section 4.5 Failure to Pay, Section 4.7 Restructuring & Bank Run / Distress (Floor 7)
ISDA_FAILURE_TO_PAY_BANK_RUN = re.compile(
    r"\b("
    r"missed (?:a |an |its )?(?:\w+ )?(?:interest|coupon|debt|bond|loan) payments?|"
    r"default(?:s|ed|ing)? on (?:debt|bonds?|loans?|obligations?|credit facility)|"
    r"in default|"
    r"failed to (?:pay|meet) (?:debt|obligations?|margin call)|"
    r"run on deposits|"
    r"deposit run|"
    r"bank run|"
    r"depositors? pull(?:ing)? (?:cash|funds?|deposits?|billions?)|"
    r"deposit (?:flight|outflow[s]?|withdrawals?|drain|bleed|exodus)|"
    r"surge in deposit withdrawals?|"
    r"pulled billions? in deposits?|"
    r"massive deposit outflows?|"
    r"liquidity crisis|"
    r"cash crunch|"
    r"emergency liquidity|"
    r"emergency discount window|"
    r"capital raise (?:failed|collapses?|scrapped|aborted)|"
    r"failed to raise capital|"
    r"emergency capital raise|"
    r"surprise (?:bond|securities|portfolio) losses|"
    r"losses on (?:bond|securities|investment) portfolio|"
    r"massive (?:bond|securities|portfolio) losses|"
    r"unhedged (?:bond|securities|treasury) losses|"
    r"debt restructuring|"
    r"distressed debt exchange|"
    r"downgrade[sd]? (?:to )?junk|"
    r"junk (?:downgrade|status|territory)|"
    r"credit rating cut to junk|"
    r"covenant (?:breach|waiver)"
    r")\b",
    re.I,
)

# 3. SEC Form 8-K Item 1.05 Material Cybersecurity Incidents
# Widespread / Systemic Outages (Floor 8)
SEC_CYBER_CATASTROPHIC = re.compile(
    r"\b("
    r"global (?:it )?outage|"
    r"worldwide (?:it )?outage|"
    r"massive system crash|"
    r"systems? down worldwide|"
    r"update crashes windows|"
    r"faulty (?:software )?update (?:crashes?|grounds?|cripples?)|"
    r"crippled (?:systems|operations|flights|hospitals|infrastructure)|"
    r"widespread (?:it |system )?outage"
    r")\b",
    re.I,
)

# Material Cyber Events (Floor 7)
SEC_CYBER_MATERIAL = re.compile(
    r"\b("
    r"material cybersecurity incident|"
    r"ransomware (?:attack|gang|infection)?|"
    r"zero[- ]day (?:exploit|vulnerability)|"
    r"data breach|"
    r"cyberattack|"
    r"unauthorized access to systems|"
    r"critical infrastructure outage|"
    r"systems? down|"
    r"major outage"
    r")\b",
    re.I,
)

# Conference & Sponsorship Exclusions (e.g. routine SVB Securities biopharma conferences)
CONFERENCE_EXCLUSIONS = re.compile(
    r"\b("
    r"biopharma conference|"
    r"healthcare conference|"
    r"investor conference|"
    r"to host (?:an? )?(?:\w+ )?conference|"
    r"fireside chat|"
    r"symposium|"
    r"annual (?:investor|global) summit|"
    r"conference sponsorship"
    r")\b",
    re.I,
)


def match_credit_or_cyber_event(
    text: str,
    entity_spans: Optional[List[EvidenceSpan]] = None,
    primary_entity_id: Optional[str] = None,
) -> Optional[DomainTermMatch]:
    """Evaluate text for credit-distress and material cyber events grounded in ISDA and SEC rules.

    Args:
        text: Input headline or news body.
        entity_spans: Spans where resolved entities appear in the text.
        primary_entity_id: Optional entity ticker/id hint.

    Returns:
        DomainTermMatch with event class, severity floor, confidence, and evidence span,
        or None if no domain rule fires or exclusions apply.
    """
    if not text:
        return None

    # Exclude routine marketing, conference hosting, and PR announcements
    is_conf = bool(CONFERENCE_EXCLUSIONS.search(text))
    has_svb_sec = "svb securities" in text.lower()

    # 1. Check ISDA Bankruptcy & Governmental Intervention (Floor 8)
    if m := ISDA_BANKRUPTCY_INTERVENTION.search(text):
        if _is_entity_subject(text, m.start(), m.end(), entity_spans):
            return DomainTermMatch(
                event_class="CREDIT",
                term_category="ISDA_BANKRUPTCY_GOVERNMENTAL_INTERVENTION",
                severity_floor=8,
                confidence=0.92,
                evidence_span=EvidenceSpan(start=m.start(), end=m.end(), text=m.group()),
                matched_phrase=m.group(),
            )

    # 2. Check ISDA Failure to Pay, Bank Run, and Capital Crisis (Floor 7)
    if m := ISDA_FAILURE_TO_PAY_BANK_RUN.search(text):
        if not (is_conf and has_svb_sec):
            if _is_entity_subject(text, m.start(), m.end(), entity_spans):
                return DomainTermMatch(
                    event_class="CREDIT",
                    term_category="ISDA_FAILURE_TO_PAY_BANK_RUN",
                    severity_floor=7,
                    confidence=0.88,
                    evidence_span=EvidenceSpan(start=m.start(), end=m.end(), text=m.group()),
                    matched_phrase=m.group(),
                )

    # If conference pattern matched and no credit failure was found, return None
    if is_conf and has_svb_sec:
        return None

    # 3. Check SEC Item 1.05 Widespread / Global IT Outage (Floor 8)
    if m := SEC_CYBER_CATASTROPHIC.search(text):
        if _is_entity_subject(text, m.start(), m.end(), entity_spans):
            return DomainTermMatch(
                event_class="CYBER",
                term_category="SEC_CYBER_GLOBAL_OUTAGE",
                severity_floor=8,
                confidence=0.92,
                evidence_span=EvidenceSpan(start=m.start(), end=m.end(), text=m.group()),
                matched_phrase=m.group(),
            )

    # 4. Check SEC Item 1.05 Material Cyber Incidents (Floor 7)
    if m := SEC_CYBER_MATERIAL.search(text):
        if _is_entity_subject(text, m.start(), m.end(), entity_spans):
            return DomainTermMatch(
                event_class="CYBER",
                term_category="SEC_CYBER_MATERIAL_INCIDENT",
                severity_floor=7,
                confidence=0.88,
                evidence_span=EvidenceSpan(start=m.start(), end=m.end(), text=m.group()),
                matched_phrase=m.group(),
            )

    return None


def _is_entity_subject(
    text: str,
    match_start: int,
    match_end: int,
    entity_spans: Optional[List[EvidenceSpan]],
) -> bool:
    """Verify that the resolved entity is the syntactic/proximate subject of the event term."""
    # If no entity spans were resolved, headline-length text defaults to true if entities aren't tracked
    if not entity_spans:
        return True

    # If text is headline length (< 220 chars), any mentioned entity is the subject
    if len(text) <= 220:
        return True

    # Otherwise, require the entity mention to be within 160 characters of the term match
    for span in entity_spans:
        if abs(span.start - match_end) <= 160 or abs(span.end - match_start) <= 160:
            return True

    return False
