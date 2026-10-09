# Open-Source Research & Implementation Decisions — S&P Sentinel

**Project:** S&P Sentinel (S&P Global & CRISIL Campus Hackathon 2026)  
**Author:** Aman Gupta (Indian Institute of Technology Kharagpur)  
**Research Method:** Systematic search and evaluation of public financial NLP, graph propagation, Kaggle benchmarks, and balance sheet stress testing libraries.

---

## 1. Selected Stack & Architectural Implementation

| Component | Selected Technology | Role in Sentinel | License & Upstream Attribution | Verification & Status |
|---|---|---|---|---|
| **Sentiment Analysis** | ProsusAI FinBERT & Financial Lexicon | Domain sentiment distribution $[-1.0, +1.0]$ with strict 3-way probability normalization | Apache-2.0 (code & weights) / Malo et al. | ✅ Fully integrated; CPU-optimized inference with lexicon fallback |
| **Event Classification** | scikit-learn Logistic / TF-IDF | 10-class financial risk taxonomy with explicit confidence thresholding and `OTHER` abstention | BSD-3-Clause | ✅ Fully integrated; trained on financial vernacular seeds |
| **Entity Extraction** | Regex Cashtags + Alias Table | True character offset (`[start, end]`) entity extraction, resolving tickers, canonical names, and cashtags | Public domain factual identifiers / MIT | ✅ Fully integrated; extracts exact spans without synthetic truncations |
| **Contagion Propagation** | NetworkX | Directed customer-supplier and creditor graph with 2-hop geometric dampening ($0.50^{\text{hop}}$) | BSD-3-Clause | ✅ Fully integrated in `src/sentinel/stress/contagion.py` |
| **Wholesale Stress Math** | NumPy / SciPy / pandas | Vectorized IFRS 9 ECL on loans, modified duration & convexity on bonds, signed DV01 on SOFR swaps | BSD-3-Clause / Apache-2.0 | ✅ Fully integrated in `src/sentinel/stress/valuation.py` |
| **Document & Slide Generation** | ReportLab & Matplotlib | Programmatic generation of `docs/presentation.pdf` and `docs/architecture.png` | BSD-style / Matplotlib license | ✅ Fully integrated; builds verified submission deliverables |
| **Backend Framework** | FastAPI & Pydantic v2 | High-performance asynchronous localhost REST API and strictly validated data contracts | MIT License | ✅ Fully integrated; strict localhost CORS |
| **Terminal UI** | React 18, TypeScript, Vite, Tailwind CSS | High-density institutional dark-mode terminal with live SSE feeds and stress waterfall | MIT License | ✅ Fully integrated; 100% offline localhost execution |

---

## 2. Public Kaggle Datasets Ingestion & Provenance

To satisfy the hackathon problem statement requirements for realistic data sources without violating Hackathon Guidelines Section 8 (confidentiality), open Kaggle datasets are ingested via dedicated converters in `scripts/data/`:

### 2.1 FinancialPhraseBank (Malo et al. 2014)
- **Kaggle Slug:** `ankurzing/sentiment-analysis-for-financial-news`
- **Upstream License:** Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
- **Role in Sentinel:** Pure offline sentiment evaluation benchmark. Converted via `scripts/data/convert_phrasebank.py` into `data/external/phrasebank/sample.csv` with detached labels `silver_labels.csv`.
- **Contamination Caveat:** FinBERT was fine-tuned on FinancialPhraseBank; hence, it is reported as an in-domain benchmark alongside independent gold holdout metrics.

### 2.2 Financial News with Ticker-Level Sentiment
- **Kaggle Slug:** `rdolphin/financial-news-with-ticker-level-sentiment`
- **Upstream License:** Creative Commons CC0 1.0 Universal (Public Domain)
- **Role in Sentinel:** Real news headlines with ticker references. Converted via `scripts/data/convert_ticker_news.py` into `data/external/ticker_news/replay_sample.csv` with detached silver labels. Primary entity fields are left blank so the entity linking engine operates organically.

### 2.3 Tweet Sentiment's Impact on Stock Returns
- **Kaggle Slug:** `thedevastator/tweet-sentiment-s-impact-on-stock-returns`
- **Upstream License:** Creative Commons CC0 1.0 Universal (Public Domain)
- **Role in Sentinel:** Real stock tweets with cashtags (`$APEX`, `$TSTEL`). Converted via `scripts/data/convert_tweets.py` into `data/external/tweets/replay_sample.csv` with detached forward return outcomes `outcomes.csv` for predictive backtesting.

### 2.4 Financial Transactions & Credit Card Analytics
- **Kaggle Slug:** `computingvictor/transactions-fraud-datasets`
- **Upstream License:** Creative Commons CC0 1.0 Universal (Public Domain)
- **Role in Sentinel:** Fulfills Problem Statement Module B ("provided sample transaction data"). Converted via `scripts/data/build_credit_sleeve.py` into `data/portfolio/credit_sleeve.csv` and `credit_sleeve.json`, aggregating user debt balances, FICO scores, and dominant MCC merchant categories into pooled consumer and SME loan tranches.

---

## 3. Engineering Decisions & Architectural Defenses

1. **CPU-First Offline Execution vs. Heavy Generative LLMs:**
   - Evaluated large open-source LLMs (Llama, Mistral) against CPU FinBERT + Logistic Classifier.
   - **Decision:** FinBERT + scikit-learn + heuristic rubric provides deterministic, sub-50ms execution on standard CPU hardware with zero external API dependencies or latency bottlenecks.
2. **Simplified Sensitivity Approximations vs. Black-Box Pricing Models:**
   - Evaluated QuantLib integration against closed-form duration, convexity, and signed DV01.
   - **Decision:** Closed-form sensitivities are completely transparent, auditable, and mathematically sound for balance sheet stress testing under hackathon guidelines.
3. **Module B Specialization vs. Toy Module A Optimization:**
   - Evaluated splitting effort between Black-Litterman index rebalancing (Module A) and Wholesale Credit Stress Testing (Module B).
   - **Decision:** Deep specialization in Module B aligns directly with the core analytical mission of S&P Global Ratings and CRISIL Credit Risk Intelligence.
