# Open-source research — S&P Sentinel

## Method and evidence limits

Research used the user's requested **Tinyfish MCP**, accessed through the existing local MCP client. Calls included `search` for financial NLP, portfolio optimization and Kaggle sources, followed by `fetch_content` on official repositories/model cards and selected dataset pages.

`tinyfish-research-evidence.json` contains raw fetched results for the primary candidate URLs. It is public-page text only, not credentials. Some additional search/model-card checks are summarized here. This note describes discovery and design recommendations, not installation, inference benchmarks or a completed dependency/license audit.

Kaggle fetches returned frontend/CSS errors. Search results located candidate datasets, but their exact downloadable schemas, row counts and upstream rights were not verified. Do not present them as acquired/approved. Model code licenses do not automatically establish checkpoint or training-data rights.

## 1. Recommended stack: fewer libraries, deeper engineering

| Component | Role | Research evidence | Selection |
|---|---|---|---|
| ProsusAI FinBERT | Financial positive/negative/neutral sentiment; numeric score from positive minus negative probability | Official repo/model card describes financial sentiment and PhraseBank fine-tuning; code repo shows Apache-2.0 | Core candidate; checkpoint redistribution terms must be checked before packaging |
| ONNX Runtime | Optional CPU/int8 inference optimization | Official repository identifies MIT license | P2 optimization, not a substitute for a measured inference benchmark |
| Sentence Transformers + all-MiniLM-L6-v2 | Semantic dedup; small text embeddings for event-classification experiments | Official framework documents embeddings/similarity; MiniLM raw model card states Apache-2.0 and 384-dimensional embeddings | Promote only if useful against TF-IDF/exact-dedup baseline |
| scikit-learn | CPU TF-IDF/logistic event classifier, calibration and metrics | Standard dependency proposed by architecture; not separately fetched in this research | Core; inspect actual selected release license at implementation |
| spaCy rules + curated aliases | High-precision entity/ticker linking | Proposed architecture choice; not separately fetched here | Core; version/model license review during setup |
| GLiNER | Optional entity mention extraction without an LLM | Official repository describes zero-shot NER and local/CPU deployment; code repo shows Apache-2.0 | Experiment only; specific checkpoint has separate terms |
| NetworkX | Small supply-chain/exposure graph | Official repository explicitly states BSD-3-Clause and graph-analysis purpose | P1 graph implementation |
| Cytoscape.js | Interactive exposure-path visualization | Official repository describes graph analysis/renderer; extracted page did not expose complete license text | P1 frontend; verify selected release's license before adoption |
| CVXPY | Constrained allocation with explicit directional/sector/turnover rules | Official code repository shows Apache-2.0 | Secondary Module A; audit chosen solver dependencies too |
| PyPortfolioOpt | Black-Litterman posterior/portfolio optimization and shrinkage | Official repository lists BL, covariance shrinkage, HRP and MIT license | P2 BL adapter; not the default PS directional policy |
| FastAPI/React/Recharts/SQLite | Local typed service, dashboard, charts and audit persistence | Architecture choices, not individually researched in this Tinyfish batch | Ordinary core tools; pin and license-check during setup |

Primary sources:
- FinBERT code: https://github.com/ProsusAI/finBERT
- FinBERT checkpoint/model card: https://huggingface.co/ProsusAI/finbert
- ONNX Runtime: https://github.com/microsoft/onnxruntime
- Sentence Transformers: https://github.com/UKPLab/sentence-transformers
- MiniLM checkpoint card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/raw/main/README.md
- GLiNER: https://github.com/urchade/GLiNER
- NetworkX: https://github.com/networkx/networkx
- Cytoscape.js: https://github.com/cytoscape/cytoscape.js
- CVXPY: https://github.com/cvxpy/cvxpy
- PyPortfolioOpt: https://github.com/PyPortfolio/PyPortfolioOpt

## 2. What makes the application distinctive

The strongest combination is **FinBERT + task-specific event classification + evidence-linked severity + duplicate-aware entity signals + bounded exposure graph + reconciled multi-asset stress + deterministic replay**.

The original engineering is in:
1. Source identity and trustworthy input/model/result lineage.
2. Entity resolution and splitting direct sentiment from inferred financial exposure.
3. Abstention for uncertain or unsupported events.
4. Suppression of repeated financial actions from syndicated/copy-pasted headlines.
5. Explicit graph transmission assumptions and traceable two-hop effects.
6. Asset-specific signed sensitivities instead of multiplying every asset by sentiment.
7. Financial invariant/property tests, no-look-ahead and real offline release verification.
8. Held-out baseline comparisons and failure cases.

A large library list is not a stronger model. Adding heavy models or optimizers without evidence makes the solo submission more brittle.

## 3. Alternative tools considered

### Riskfolio-Lib
Tinyfish search identified the official documentation: https://riskfolio-lib.readthedocs.io/en/latest/ . Its snippet describes a portfolio optimization library built on CVXPY/pandas. It is an alternative if richer portfolio-risk methods become a justified priority, not another mandatory dependency. Its selected version, dependencies and license still require direct inspection.

### skfolio
Tinyfish search identified https://skfolio.org/ . Its official-result snippet describes portfolio optimization/factor modeling/risk management and a BSD-3-Clause license. Consider as an alternative research path, but do not combine it with PyPortfolioOpt and Riskfolio without a specific requirement. Not installed or benchmarked.

### QuantLib / heavy pricing libraries
Not researched/validated in this Tinyfish batch. Full derivative pricing may be useful in a later product, but is unnecessary for the PS's explicitly permitted simplified stress model. A transparent tested sensitivity approximation is preferable to an opaque partial integration.

### Large local generative LLMs / agent frameworks
Not required. Structured inference and deterministic evidence templates are less resource-intensive and easier to evaluate. An agent framework does not solve missing labels, event-time alignment or inaccurate bond/swap units.

## 4. Dataset discoveries and gates

### Kaggle financial news / FinancialPhraseBank
https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news

Tinyfish search describes sentiment plus news headlines. A focused search reports **CC BY-NC-SA 4.0**. The actual fetched page crashed, so confirm upstream license and dataset files before bundling. Do not relicense the data under the project's MIT license.

FinBERT's own official documentation says it was fine-tuned on FinancialPhraseBank. Therefore performance here is not proof of independent out-of-sample generalization. Use it as an in-domain benchmark with a contamination caveat; independently annotate a separate holdout.

### Kaggle stock-related tweets
https://www.kaggle.com/datasets/thedevastator/tweet-sentiment-s-impact-on-stock-returns

Search describes labeled tweets and associated returns. Fetch failed at the frontend. Check original collection source, exact fields, labels, time coverage, redistribution rights and platform terms. Do not declare the search-advertised row count as the actual loaded count.

### Kaggle entity-linked financial news
https://www.kaggle.com/datasets/rdolphin/financial-news-with-ticker-level-sentiment/data

Search candidate only; no detailed fetch in the evidence file. It may help entity-level analysis, but check origin, timestamps, rights and label-generation methodology. Machine-generated sentiment labels are not independent human ground truth.

### Optional alternative social dataset
https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment

Tinyfish fetched the dataset card/viewer. The card states MIT, English finance tweets and three labels: bearish, bullish, neutral. Card split counts differ from the viewer's totals; use the actual downloaded files and programmatic counts. The page does not establish genuine publication timestamps for every row. It is an optional alternative if a responsibly distributable Kaggle dataset is unavailable, not a mandatory departure from the user's Kaggle-first preference.

### Rights-safe synthetic scenario path
Authored news and social-style records can provide realistic offline demonstration coverage if external rights remain unclear. Label every synthetic record and never imply these were collected real posts/news. This improves reproducibility, but replay-only/synthetic ingestion's fit to the PS's real-time objective must be disclosed.

## 5. Adoption checklist

Before any library/model/dataset is promoted into the build:
- Resolve an exact package version/model revision/dataset version.
- Check original license and notices; inspect transitive dependencies and solvers.
- Confirm checkpoint redistribution independently of code license.
- Confirm public data redistribution, upstream rights and share-alike/noncommercial obligations where applicable.
- Record checksums and data counts using code, not search snippets.
- Run a CPU-only proof-of-concept and measure quality, latency and memory.
- Validate offline loading with external networking denied.
- Promote only if it satisfies a concrete acceptance criterion.
- Keep attribution and distinguish project-created work from reused components.

No package install, dataset acquisition, checkpoint download, training run or model-quality benchmark was performed as part of this PRD-only task.
