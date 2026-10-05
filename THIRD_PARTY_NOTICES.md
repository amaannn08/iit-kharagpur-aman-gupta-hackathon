# Third-Party Notices & Open-Source Licensing

This project incorporates open-source software and references models/libraries identified in `docs/OPEN_SOURCE_RESEARCH.md`. All dependencies and candidate models are governed by their respective licenses as detailed below.

---

## 1. Core Backend Libraries

### FastAPI
- **License:** MIT License
- **Copyright:** (c) 2018 Sebastián Ramírez
- **URL:** https://github.com/fastapi/fastapi

### Pydantic & Pydantic-Settings
- **License:** MIT License
- **Copyright:** (c) 2017 Samuel Colvin and contributors
- **URL:** https://github.com/pydantic/pydantic

### SQLAlchemy
- **License:** MIT License
- **Copyright:** (c) 2005-2024 Michael Bayer and contributors
- **URL:** https://www.sqlalchemy.org/

### Pandas
- **License:** BSD-3-Clause
- **Copyright:** (c) 2008-2011 AQR Capital Management, LLC, Lambda Foundry, Inc. and PyData Development Team
- **URL:** https://pandas.pydata.org/

### NumPy
- **License:** BSD-3-Clause
- **Copyright:** (c) 2005-2024 NumPy Developers
- **URL:** https://numpy.org/

### SciPy
- **License:** BSD-3-Clause
- **Copyright:** (c) 2001-2024 SciPy Developers
- **URL:** https://scipy.org/

### NetworkX
- **License:** BSD-3-Clause
- **Copyright:** (c) 2004-2024 NetworkX Developers
- **URL:** https://github.com/networkx/networkx

---

## 2. Frontend Libraries

### React & React-DOM
- **License:** MIT License
- **Copyright:** (c) Meta Platforms, Inc. and affiliates
- **URL:** https://github.com/facebook/react

### Vite
- **License:** MIT License
- **Copyright:** (c) 2019-present Evan You & Vite Contributors
- **URL:** https://github.com/vitejs/vite

### Tailwind CSS
- **License:** MIT License
- **Copyright:** (c) Tailwind Labs, Inc.
- **URL:** https://tailwindcss.com/

### Lucide Icons
- **License:** ISC License
- **Copyright:** (c) 2022 Lucide Contributors
- **URL:** https://lucide.dev/

---

## 3. Researched AI/Quant Models & Candidates (P1/P2 Roadmap)

### ProsusAI / finBERT
- **Code License:** Apache-2.0
- **Model Checkpoint:** Pinned revision on Hugging Face (`ProsusAI/finbert`)
- **Citation/Source:** ProsusAI (Araci, 2019)
- **Notice:** Trained/fine-tuned on FinancialPhraseBank. Redistribution terms and local caching rules documented in `docs/OPEN_SOURCE_RESEARCH.md`.

### all-MiniLM-L6-v2
- **License:** Apache-2.0
- **Authors:** Sentence-Transformers / Hugging Face
- **URL:** https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

### CVXPY
- **License:** Apache-2.0
- **Copyright:** (c) 2013-2024 Steven Diamond, Eric Chu, Stephen Boyd and contributors
- **URL:** https://github.com/cvxpy/cvxpy

### PyPortfolioOpt
- **License:** MIT License
- **Copyright:** (c) 2019 Robert Martin
- **URL:** https://github.com/PyPortfolio/PyPortfolioOpt

---

## 4. Synthetic Data Notice

All bundled datasets in `data/` (`news_demo.csv`, `social_demo.csv`, `wholesale_positions.json`, `entity_aliases.csv`, `graph_edges.csv`, and scenario files) are authored synthetic datasets created specifically for this hackathon evaluation. They contain **zero** confidential, proprietary, or private data from S&P Global, CRISIL, or their clients, fully complying with Hackathon Guidelines Section 8.
