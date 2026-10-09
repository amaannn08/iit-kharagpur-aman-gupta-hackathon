"""Script to generate the frozen, independent 105-row NLP evaluation holdout dataset.

Conforms to PRD Section 4.2 & 13.1 and Review Plan P0-3:
- Independent of seed training examples (no leakage).
- Stratified across 10 event classes (10-12 samples each).
- Includes adversarial and edge-case samples.
- Pre-labeled ground truth for entity, sentiment (label + score), event class, and severity (1-10).
"""

import csv
from pathlib import Path

HOLDOUT_ROWS = [
    # --- CREDIT (11 samples) ---
    ("eval-001", "Apex Industrial Holdings credit facility downgraded to junk by Moody's amid widening liquidity deficit.", "APEX", "negative", -0.85, "CREDIT", 8, "false"),
    ("eval-002", "Senior bondholders of Apex Industrial form restructuring committee following missed coupon payment on notes.", "APEX", "negative", -0.90, "CREDIT", 9, "false"),
    ("eval-003", "Starlight Energy successfully refinances $850M syndicated debt facility with five major commercial banks.", "SLEN", "positive", 0.70, "CREDIT", 3, "false"),
    ("eval-004", "Titan Steel negotiates covenant waiver with primary lending syndicate ahead of quarterly compliance audit.", "TSTEL", "neutral", 0.05, "CREDIT", 5, "false"),
    ("eval-005", "Global Logistics faces potential technical covenant breach if freight operating margin compresses further.", "GLOG", "negative", -0.65, "CREDIT", 6, "false"),
    ("eval-006", "FinSecure Bank secures emergency liquidity window access following sudden commercial deposit outflows.", "FSBK", "negative", -0.80, "CREDIT", 8, "false"),
    ("eval-007", "Meridian Financial reports non-performing wholesale loans rose 15 basis points to 1.1% of portfolio.", "MFIN", "negative", -0.45, "CREDIT", 4, "false"),
    ("eval-008", "Apex Industrial denies market speculation regarding chapter 11 bankruptcy filing and affirms liquidity.", "APEX", "positive", 0.35, "CREDIT", 3, "true"),
    ("eval-009", "S&P Global Ratings lowers credit rating of Quantum Semiconductor to BBB- with stable outlook.", "QSEM", "negative", -0.60, "CREDIT", 6, "false"),
    ("eval-010", "Commercial paper redemption completed smoothly without drawing on backup credit line.", "MACRO", "positive", 0.40, "CREDIT", 2, "false"),
    ("eval-011", "Distressed debt exchange announced by regional industrial fabricator offering 70 cents on the dollar.", "APEX", "negative", -0.82, "CREDIT", 8, "false"),

    # --- MACRO (11 samples) ---
    ("eval-012", "Federal Reserve raises target federal funds rate by 50 basis points to combat persistent inflation.", "MACRO", "negative", -0.70, "MACRO", 8, "false"),
    ("eval-013", "Federal Reserve cuts benchmark interest rate 50 basis points in emergency move to support liquidity.", "MACRO", "positive", 0.65, "MACRO", 7, "false"),
    ("eval-014", "Headline consumer price index rose 0.4% month over month, exceeding consensus forecast of 0.2%.", "MACRO", "negative", -0.55, "MACRO", 6, "false"),
    ("eval-015", "Benchmark 10-year Treasury yields surged 18 basis points to 4.65% following strong non-farm payrolls.", "MACRO", "negative", -0.60, "MACRO", 7, "false"),
    ("eval-016", "European Central Bank leaves benchmark refinancing rates unchanged at 3.75% during policy meeting.", "MACRO", "neutral", 0.00, "MACRO", 2, "false"),
    ("eval-017", "US gross domestic product expanded at an annualized rate of 2.8% in the third quarter beating forecasts.", "MACRO", "positive", 0.75, "MACRO", 4, "false"),
    ("eval-018", "Manufacturing purchasing managers index contracted to 47.2 signaling continued factory output slowdown.", "MACRO", "negative", -0.50, "MACRO", 5, "false"),
    ("eval-019", "Central bank governor states policy rates are in restrictive territory and monetary easing is likely.", "MACRO", "positive", 0.50, "MACRO", 4, "false"),
    ("eval-020", "Yield curve inverts further as 2-year Treasury note yields exceed 10-year bonds by 35 basis points.", "MACRO", "negative", -0.65, "MACRO", 6, "false"),
    ("eval-021", "Unemployment rate held steady at 4.1% while labor force participation rate edged down slightly.", "MACRO", "neutral", 0.05, "MACRO", 2, "false"),
    ("eval-022", "Federal Reserve maintains interest rates steady, defying calls from politicians for immediate cuts.", "MACRO", "neutral", -0.05, "MACRO", 3, "true"),

    # --- GEOPOLITICAL (11 samples) ---
    ("eval-023", "New trade sanctions imposed on critical mineral exports, halting global lithium and cobalt shipments.", "LITH", "negative", -0.80, "GEOPOLITICAL", 8, "false"),
    ("eval-024", "Naval conflict closes commercial shipping transit through strategic maritime strait, driving crude up 6%.", "SLEN", "negative", -0.85, "GEOPOLITICAL", 8, "false"),
    ("eval-025", "Government officials sign bilateral trade pact reducing tariffs on industrial machinery and steel.", "CAT", "positive", 0.70, "GEOPOLITICAL", 4, "false"),
    ("eval-026", "Export controls expanded to restrict advanced semiconductor manufacturing equipment sales overseas.", "QSEM", "negative", -0.75, "GEOPOLITICAL", 7, "false"),
    ("eval-027", "Foreign state regulatory agency nationalizes onshore renewable energy assets of international utility.", "SLEN", "negative", -0.90, "GEOPOLITICAL", 9, "false"),
    ("eval-028", "Cross-border border dispute threatens natural gas pipeline transmission into Central Europe.", "SLEN", "negative", -0.78, "GEOPOLITICAL", 8, "false"),
    ("eval-029", "Diplomatic delegation agrees to framework to protect undersea telecommunications fiber cables.", "PTEL", "positive", 0.55, "GEOPOLITICAL", 3, "false"),
    ("eval-030", "Retaliatory tariff schedule announced on imported European automotive vehicles and industrial parts.", "VAUTO", "negative", -0.70, "GEOPOLITICAL", 7, "false"),
    ("eval-031", "International maritime court dismisses territorial claim against deep-sea logistics shipping routes.", "GLOG", "positive", 0.40, "GEOPOLITICAL", 3, "false"),
    ("eval-032", "Security council votes to freeze sovereign foreign currency assets of aggressive neighboring state.", "MACRO", "negative", -0.75, "GEOPOLITICAL", 8, "false"),
    ("eval-033", "Defense ministry signs bilateral cooperation treaty without altering corporate trade guidelines.", "MACRO", "neutral", 0.00, "GEOPOLITICAL", 2, "true"),

    # --- SUPPLY_CHAIN (11 samples) ---
    ("eval-034", "Titan Steel blast furnace suffered major industrial fire, halting steel coil shipments nationwide.", "TSTEL", "negative", -0.88, "SUPPLY_CHAIN", 8, "false"),
    ("eval-035", "Dockworkers strike shuts down container terminal operations at West Coast commercial ports.", "GLOG", "negative", -0.82, "SUPPLY_CHAIN", 8, "false"),
    ("eval-036", "Critical shortage of microcontrollers forces Vanguard Auto to suspend assembly lines for two weeks.", "VAUTO", "negative", -0.75, "SUPPLY_CHAIN", 7, "false"),
    ("eval-037", "Lithium One completes expansion of brine extraction facility, doubling battery-grade raw material output.", "LITH", "positive", 0.80, "SUPPLY_CHAIN", 4, "false"),
    ("eval-038", "Freight rail carrier resolves labor dispute with conductor union, averting national rail embargo.", "GLOG", "positive", 0.65, "SUPPLY_CHAIN", 3, "false"),
    ("eval-039", "Container turnaround times at regional transshipment hubs spike to 18 days due to customs backlogs.", "GLOG", "negative", -0.60, "SUPPLY_CHAIN", 6, "false"),
    ("eval-040", "Chemical supplier declares force majeure on ethylene oxide production following severe weather.", "TSTEL", "negative", -0.70, "SUPPLY_CHAIN", 7, "false"),
    ("eval-041", "Global Logistics signs multi-year maritime freight charter securing container carrier fleet capacity.", "GLOG", "positive", 0.60, "SUPPLY_CHAIN", 3, "false"),
    ("eval-042", "Semiconductor wafer fabrication plant resumes standard operational capacity ahead of deadline.", "QSEM", "positive", 0.72, "SUPPLY_CHAIN", 3, "false"),
    ("eval-043", "Raw material inventory stockpiles buffer Titan Steel from minor freight delays.", "TSTEL", "neutral", 0.10, "SUPPLY_CHAIN", 2, "true"),
    ("eval-044", "Air cargo freight spot rates tumble 14% as belly-hold international passenger capacity expands.", "GLOG", "negative", -0.40, "SUPPLY_CHAIN", 4, "false"),

    # --- EARNINGS (11 samples) ---
    ("eval-045", "Meridian Financial reports record net income of $480M with commercial net interest margin expanding.", "MFIN", "positive", 0.88, "EARNINGS", 4, "false"),
    ("eval-046", "Caterpillar quarterly revenue dropped 6% as heavy construction machinery demand cooled globally.", "CAT", "negative", -0.60, "EARNINGS", 5, "false"),
    ("eval-047", "Apple posts quarterly earnings per share of $1.64 beating analyst estimates of $1.58 on services growth.", "AAPL", "positive", 0.75, "EARNINGS", 4, "false"),
    ("eval-048", "Apex Industrial cuts full-year revenue outlook by 18% citing weaker customer orders in heavy fabrication.", "APEX", "negative", -0.78, "EARNINGS", 7, "false"),
    ("eval-049", "Microsoft quarterly cloud revenue surges 29% driven by enterprise AI infrastructure deployments.", "MSFT", "positive", 0.85, "EARNINGS", 4, "false"),
    ("eval-050", "ExxonMobil operating profit falls 12% as crude oil and refining margins retreat from cyclical peaks.", "XOM", "negative", -0.55, "EARNINGS", 5, "false"),
    ("eval-051", "JPMorgan Chase net interest income surpasses guidance with consumer credit losses remaining modest.", "JPM", "positive", 0.80, "EARNINGS", 4, "false"),
    ("eval-052", "Boeing quarterly cash burn worsens as commercial aircraft deliveries decline to 24 units.", "BA", "negative", -0.80, "EARNINGS", 7, "false"),
    ("eval-053", "Starlight Energy quarterly EBITDA rises 22% on higher solar generation and regulated power tariffs.", "SLEN", "positive", 0.78, "EARNINGS", 3, "false"),
    ("eval-054", "Walmart comparable store sales increase 4.2% while inventory levels remain lean across warehouses.", "WMT", "positive", 0.65, "EARNINGS", 3, "false"),
    ("eval-055", "Company reports earnings exactly in line with consensus guidance with zero change in dividend policy.", "AAPL", "neutral", 0.02, "EARNINGS", 2, "true"),

    # --- M_AND_A (10 samples) ---
    ("eval-056", "Starlight Energy signs definitive agreement to acquire SolarWave Infrastructure for $4.8B in cash.", "SLEN", "positive", 0.40, "M_AND_A", 6, "false"),
    ("eval-057", "Activist investor launches hostile tender offer to acquire outstanding common stock of Apex Industrial.", "APEX", "neutral", 0.05, "M_AND_A", 7, "false"),
    ("eval-058", "Meridian Financial agrees to sell non-core residential mortgage servicing rights for $320M cash.", "MFIN", "positive", 0.50, "M_AND_A", 4, "false"),
    ("eval-059", "DataCloud terminates planned acquisition of CloudSecure following failure to agree on final terms.", "DCLD", "negative", -0.50, "M_AND_A", 6, "false"),
    ("eval-060", "Board of directors of Lithium One approves merger of equals with Australian mining consortium.", "LITH", "positive", 0.45, "M_AND_A", 6, "false"),
    ("eval-061", "Vanguard Auto announces strategic equity investment in next-generation solid-state battery developer.", "VAUTO", "positive", 0.60, "M_AND_A", 4, "false"),
    ("eval-062", "Private equity firm completes leveraged buyout of regional logistics warehousing operator.", "GLOG", "neutral", 0.10, "M_AND_A", 5, "false"),
    ("eval-063", "Regulatory authorities approve telecom infrastructure merger without imposing asset divestitures.", "PTEL", "positive", 0.65, "M_AND_A", 4, "false"),
    ("eval-064", "Pfizer completes $14B acquisition of commercial-stage oncology therapeutic biotechnology company.", "PFE", "positive", 0.55, "M_AND_A", 5, "false"),
    ("eval-065", "Company rejects preliminary takeover approach indicating bid undervalues long-term asset value.", "APEX", "neutral", -0.05, "M_AND_A", 4, "true"),

    # --- REGULATORY (10 samples) ---
    ("eval-066", "DOJ files antitrust lawsuit seeking to block Quantum Semiconductor from acquiring rival chipmaker.", "QSEM", "negative", -0.75, "REGULATORY", 7, "false"),
    ("eval-067", "SEC initiates formal investigation into accounting practices and deferred revenue recognition at Apex.", "APEX", "negative", -0.80, "REGULATORY", 7, "false"),
    ("eval-068", "Banking regulators issue formal consent order requiring FinSecure to remediate anti-money laundering controls.", "FSBK", "negative", -0.70, "REGULATORY", 6, "false"),
    ("eval-069", "Federal Trade Commission approves joint venture agreement subject to behavioral licensing remedies.", "CAT", "positive", 0.45, "REGULATORY", 3, "false"),
    ("eval-070", "Environmental protection agency levies $42M civil penalty on Titan Steel for emissions non-compliance.", "TSTEL", "negative", -0.65, "REGULATORY", 6, "false"),
    ("eval-071", "Commodity Futures Trading Commission concludes routine market surveillance review with no findings.", "MFIN", "positive", 0.30, "REGULATORY", 2, "false"),
    ("eval-072", "Data protection authority fines DataCloud for customer privacy disclosure violations under GDPR.", "DCLD", "negative", -0.60, "REGULATORY", 5, "false"),
    ("eval-073", "Energy regulatory commission grants certificate of public convenience for interstate transmission line.", "SLEN", "positive", 0.60, "REGULATORY", 3, "false"),
    ("eval-074", "Securities regulator closes informal inquiry into executive stock trading without enforcement action.", "AAPL", "positive", 0.35, "REGULATORY", 2, "true"),
    ("eval-075", "Consumer financial protection bureau files enforcement complaint against non-bank commercial lender.", "MFIN", "negative", -0.68, "REGULATORY", 6, "false"),

    # --- CYBER (10 samples) ---
    ("eval-076", "Critical zero-day vulnerability in CloudSecure gateway actively exploited to exfiltrate database records.", "CSEC", "negative", -0.88, "CYBER", 8, "false"),
    ("eval-077", "Ransomware gang encrypts core transaction servers at FinSecure Bank, halting payment processing.", "FSBK", "negative", -0.92, "CYBER", 9, "false"),
    ("eval-078", "DataCloud successfully isolates distributed denial of service attack on public DNS nameservers.", "DCLD", "positive", 0.50, "CYBER", 3, "false"),
    ("eval-079", "Malicious code injection discovered in open source library dependency used across enterprise applications.", "CSEC", "negative", -0.70, "CYBER", 7, "false"),
    ("eval-080", "Unauthorized intrusion into internal corporate network detected; forensic audit confirms no data stolen.", "AAPL", "neutral", 0.05, "CYBER", 3, "true"),
    ("eval-081", "Cybersecurity agency issues emergency security directive mandating immediate firewall patch deployment.", "CSEC", "negative", -0.60, "CYBER", 6, "false"),
    ("eval-082", "Data extortion group threatens to publish stolen source code from Quantum Semiconductor repositories.", "QSEM", "negative", -0.80, "CYBER", 8, "false"),
    ("eval-083", "Pacific Telecom detects and neutralizes targeted state-sponsored spear-phishing campaign on staff.", "PTEL", "positive", 0.40, "CYBER", 3, "false"),
    ("eval-084", "Credential stuffing wave compromises 45,000 online banking customer credentials at regional bank.", "FSBK", "negative", -0.75, "CYBER", 7, "false"),
    ("eval-085", "Independent penetration test certifies CloudSecure next-generation zero trust architecture.", "CSEC", "positive", 0.70, "CYBER", 2, "false"),

    # --- PRODUCT (10 samples) ---
    ("eval-086", "BioHealth Pharma receives priority FDA approval for breakthrough oncology treatment drug.", "BHPH", "positive", 0.90, "PRODUCT", 4, "false"),
    ("eval-087", "Vanguard Auto issues voluntary recall of 120,000 electric vehicles over high-voltage wiring defect.", "VAUTO", "negative", -0.70, "PRODUCT", 6, "false"),
    ("eval-088", "Quantum Semiconductor launches flagship 3nm graphics processing unit with 40% performance gain.", "QSEM", "positive", 0.85, "PRODUCT", 3, "false"),
    ("eval-089", "Late-stage clinical trial of autoimmune therapy drug fails to meet primary statistical endpoint.", "BHPH", "negative", -0.85, "PRODUCT", 8, "false"),
    ("eval-090", "Pacific Telecom completes activation of transpacific high-speed subsea optical cable network.", "PTEL", "positive", 0.75, "PRODUCT", 3, "false"),
    ("eval-091", "Federal aviation administration clears next-generation commercial passenger aircraft for flight testing.", "BA", "positive", 0.70, "PRODUCT", 4, "false"),
    ("eval-092", "BioHealth Pharma reports positive top-line safety data from phase 2 clinical trial cohort.", "BHPH", "positive", 0.65, "PRODUCT", 3, "false"),
    ("eval-093", "Patent litigation court issues preliminary injunction halting distribution of flagship mobile handset.", "AAPL", "negative", -0.72, "PRODUCT", 6, "false"),
    ("eval-094", "Company rolls out annual minor software maintenance update with routine bug fixes.", "MSFT", "neutral", 0.05, "PRODUCT", 1, "true"),
    ("eval-095", "Commercial deployment of utility-scale battery energy storage system commences in Texas.", "SLEN", "positive", 0.65, "PRODUCT", 3, "false"),

    # --- OTHER (10 samples) ---
    ("eval-096", "Apple schedules annual meeting of shareholders for March 15 to vote on corporate director slate.", "AAPL", "neutral", 0.02, "OTHER", 1, "false"),
    ("eval-097", "Microsoft board declares regular quarterly cash dividend of $0.75 per common share.", "MSFT", "neutral", 0.05, "OTHER", 1, "false"),
    ("eval-098", "Caterpillar updates corporate sustainability and emissions reduction governance committee charter.", "CAT", "neutral", 0.00, "OTHER", 1, "false"),
    ("eval-099", "Meridian Financial senior executive appointed to serve on industry banking advisory board.", "MFIN", "neutral", 0.05, "OTHER", 1, "false"),
    ("eval-100", "Starlight Energy uploads presentation slides for upcoming institutional investor conference webcast.", "SLEN", "neutral", 0.00, "OTHER", 1, "false"),
    ("eval-101", "Titan Steel publishes annual corporate social responsibility report and safety disclosures.", "TSTEL", "neutral", 0.01, "OTHER", 1, "false"),
    ("eval-102", "ExxonMobil common stock begins trading ex-dividend following scheduled dividend declaration.", "XOM", "neutral", 0.00, "OTHER", 1, "false"),
    ("eval-103", "Commercial bank confirms standard holiday operating hours for regional branch locations.", "JPM", "neutral", 0.00, "OTHER", 1, "false"),
    ("eval-104", "Enterprise technology vendor announces routine transition of chief accounting officer to new role.", "MSFT", "neutral", -0.02, "OTHER", 2, "true"),
    ("eval-105", "Quarterly investor relations calendar released with upcoming earnings disclosure dates.", "CAT", "neutral", 0.00, "OTHER", 1, "false"),
]


def write_holdout_csv(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "eval_id",
        "text",
        "gold_entity",
        "gold_sentiment_label",
        "gold_sentiment_score",
        "gold_event_class",
        "gold_severity_score",
        "is_adversarial",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for row in HOLDOUT_ROWS:
            writer.writerow(row)
    print(f"Generated {len(HOLDOUT_ROWS)} holdout samples at {output_path}")


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent.parent / "data" / "eval" / "holdout_seed.csv"
    write_holdout_csv(target)
