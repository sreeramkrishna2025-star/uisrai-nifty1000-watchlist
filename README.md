# uisrai-nifty1000-watchlist

PUBLIC repo. Official NSE Nifty 1000 constituent list (name, symbol, ISIN, industry).

- Source: NSE Indices official CSV (niftyindices.com / NSE archives).
- No price data, no FYERS data, no secrets, no app code.
- Workflow: manual trigger (`workflow_dispatch`). Schedule not enabled yet.
- Validation: exactly 1000 constituents, no duplicate symbols, all Nifty 500 symbols included.
- Output: `data/nifty1000/master.csv`, `data/nifty1000/report.md`.
