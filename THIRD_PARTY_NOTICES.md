# Third-Party Notices & Open-Source Licensing

This project incorporates open-source software and references candidate libraries identified during design research (`docs/OPEN_SOURCE_RESEARCH.md`). All dependencies and candidate models are governed by their respective licenses as detailed below.

---

## 1. Currently Shipped & Bundled Runtime Dependencies

The following open-source dependencies are currently declared in `pyproject.toml` / `requirements.txt` (backend) and `frontend/package.json` (frontend), and are installed in the local environment:

### Backend Libraries
- **FastAPI**
  - **License:** MIT License
  - **Copyright:** (c) 2018 Sebastián Ramírez
  - **URL:** https://github.com/fastapi/fastapi
- **Pydantic & Pydantic-Settings**
  - **License:** MIT License
  - **Copyright:** (c) 2017 Samuel Colvin and contributors
  - **URL:** https://github.com/pydantic/pydantic
- **SQLAlchemy**
  - **License:** MIT License
  - **Copyright:** (c) 2005-2024 Michael Bayer and contributors
  - **URL:** https://www.sqlalchemy.org/
- **Pandas**
  - **License:** BSD-3-Clause
  - **Copyright:** (c) 2008-2011 AQR Capital Management, LLC, Lambda Foundry, Inc. and PyData Development Team
  - **URL:** https://pandas.pydata.org/
- **NumPy**
  - **License:** BSD-3-Clause
  - **Copyright:** (c) 2005-2024 NumPy Developers
  - **URL:** https://numpy.org/
- **SciPy**
  - **License:** BSD-3-Clause
  - **Copyright:** (c) 2001-2024 SciPy Developers
  - **URL:** https://scipy.org/
- **NetworkX**
  - **License:** BSD-3-Clause
  - **Copyright:** (c) 2004-2024 NetworkX Developers
  - **URL:** https://github.com/networkx/networkx
- **Uvicorn**
  - **License:** BSD-3-Clause
  - **Copyright:** (c) 2017-present Encode OSS Ltd.
  - **URL:** https://www.uvicorn.org/
- **pytest & pytest-asyncio**
  - **License:** MIT License
  - **Copyright:** (c) 2004-2024 Holger Krekel and contributors
  - **URL:** https://github.com/pytest-dev/pytest
- **Ruff**
  - **License:** MIT License / Apache-2.0
  - **Copyright:** (c) 2023 Astral Software Inc.
  - **URL:** https://github.com/astral-sh/ruff

### Frontend Libraries
- **React & React-DOM**
  - **License:** MIT License
  - **Copyright:** (c) Meta Platforms, Inc. and affiliates
  - **URL:** https://github.com/facebook/react
- **Vite**
  - **License:** MIT License
  - **Copyright:** (c) 2019-present Evan You & Vite Contributors
  - **URL:** https://github.com/vitejs/vite
- **Tailwind CSS**
  - **License:** MIT License
  - **Copyright:** (c) Tailwind Labs, Inc.
  - **URL:** https://tailwindcss.com/
- **Lucide Icons**
  - **License:** ISC License
  - **Copyright:** (c) 2022 Lucide Contributors
  - **URL:** https://lucide.dev/
- **Vitest**
  - **License:** MIT License
  - **Copyright:** (c) 2021-present Anthony Fu and Vitest contributors
  - **URL:** https://github.com/vitest-dev/vitest

---

## 2. Researched AI/Quant Candidates & Upstream Models (P1/P2 Roadmap — NOT BUNDLED)

> [!IMPORTANT]
> **NO model checkpoints, neural weights, or unverified packages are bundled with this repository.**
> The following entries represent candidate technologies evaluated during open-source research and architectural planning (`docs/OPEN_SOURCE_RESEARCH.md`). No redistribution of weights is made. Any eventual deployment will require local user downloading subject to upstream model card terms.

- **ProsusAI / finBERT**
  - **Code License:** Apache-2.0
  - **Model Architecture / Upstream Authors:** Dogu Araci / Prosus AI (2019)
  - **Notice:** Candidate for local CPU inference in milestone M3. Model weights are NOT bundled in this repository. Any deployment requires fetching directly from upstream Hugging Face hub under Apache-2.0 terms.
- **sentence-transformers / all-MiniLM-L6-v2**
  - **License:** Apache-2.0
  - **Authors:** Sentence-Transformers / Hugging Face
  - **Notice:** Candidate for semantic entity retrieval. Weights are NOT bundled.
- **CVXPY**
  - **License:** Apache-2.0
  - **Copyright:** (c) 2013-2024 Steven Diamond, Eric Chu, Stephen Boyd and contributors
  - **Notice:** Candidate convex optimization library for portfolio rebalancing.
- **PyPortfolioOpt**
  - **License:** MIT License
  - **Copyright:** (c) 2019 Robert Martin
  - **Notice:** Candidate for mean-variance frontier comparisons.

---

## 3. Authored Synthetic Data Licensing & Provenance Notice

All bundled datasets in `data/` (`news_demo.csv`, `social_demo.csv`, `wholesale_positions.json`, `graph_edges.csv`, scenario JSONs, and holdout seeds) are authored synthetic datasets created specifically for this hackathon evaluation by Aman Gupta.

- **License:** MIT License (Project-Authored Synthetic Data & Rubric, consistent with root `LICENSE`).
- **Provenance Details:** Fully documented in [`data/DATA_LICENSE.md`](data/DATA_LICENSE.md) and cryptographically audited in [`data/manifest.json`](data/manifest.json).
- **Public Reference Universe:** Factual identifiers (ticker symbols, company names, sectors) in `data/entity_aliases.csv` are non-copyrightable public market facts.
- **Hypothetical Relationships:** Contagion edges and wholesale banking positions are purely hypothetical simulation fixtures and do not reflect any confidential client data from S&P Global, CRISIL, or their partners.
