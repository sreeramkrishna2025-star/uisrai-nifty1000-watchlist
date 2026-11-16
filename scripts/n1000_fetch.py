"""Nifty 1000 constituent list from the official NSE Indices CSV -> data/nifty1000/.

Public repo: constituent names, symbols, ISIN and industry only (official NSE index data).
No price data, no FYERS data, no secrets, no app code.

Blocking checks: exactly 1000 real constituents, no duplicate symbol.
Blocking check: every Nifty 500 symbol (fetched from the official Nifty 500 CSV) is inside the Nifty 1000 list.
master.csv is written only when every blocking check passes. A failure keeps the previous file.
"""
import csv, io, os, sys, datetime, urllib.request

NIFTY1000_SOURCES = [
    "https://www.niftyindices.com/IndexConstituent/ind_nifty1000list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_nifty1000list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty1000list.csv",
]
NIFTY500_SOURCES = [
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
]
D = "data/nifty1000"
MASTER, REPORT = f"{D}/master.csv", f"{D}/report.md"
FIELDS = ["Company Name", "Industry", "Symbol", "Series", "ISIN Code"]
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).date().isoformat()
EXPECTED = 1000
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36",
      "Accept": "text/csv,*/*", "Referer": "https://www.niftyindices.com/"}


def fetch_csv(sources, label):
    errs = []
    for u in sources:
        try:
            req = urllib.request.Request(u, headers=UA)
            txt = urllib.request.urlopen(req, timeout=40).read().decode("utf-8-sig", "replace")
            rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(txt))]
            if not rows or not all(f in rows[0] for f in FIELDS):
                raise ValueError("columns galat: " + ",".join(rows[0].keys() if rows else []))
            return u, rows
        except Exception as e:
            errs.append(f"{u}: {e}")
    raise SystemExit(f"Official {label} list nahi mili:\n" + "\n".join(errs))


def main():
    src, rows = fetch_csv(NIFTY1000_SOURCES, "Nifty 1000")
    _, rows500 = fetch_csv(NIFTY500_SOURCES, "Nifty 500")
    real = [r for r in rows if r["Symbol"] and not r["Symbol"].startswith("DUMMY")]
    syms = [r["Symbol"] for r in real]
    dup = sorted({s for s in syms if syms.count(s) > 1})
    n500 = {r["Symbol"] for r in rows500 if r["Symbol"] and not r["Symbol"].startswith("DUMMY")}
    missing = sorted(n500 - set(syms))
    no_isin = [r["Symbol"] for r in real if not r.get("ISIN Code")]
    problems = []
    if len(real) != EXPECTED:
        problems.append(f"Constituent count {len(real)} (DUMMY chhod ke), {EXPECTED} hona chahiye")
    if dup:
        problems.append("Duplicate symbol: " + ", ".join(dup))
    if missing:
        problems.append(f"Nifty 500 ke {len(missing)} symbols Nifty 1000 list mein nahi: " + ", ".join(missing[:20]))
    lines = ["# Nifty 1000 constituent list", "",
             f"- Check: {TODAY} (IST)", f"- Source: {src}",
             f"- Nifty 1000 constituents: {len(real)}",
             f"- Nifty 500 symbols (official list): {len(n500)}",
             f"- Nifty 500 ke saare symbols Nifty 1000 mein: {'haan' if not missing else 'nahi'}",
             f"- ISIN missing (kisi ISIN ko invent nahi kiya): {len(no_isin)}"]
    ok = not problems
    if problems:
        lines += ["", "## BLOCKING: master.csv NAHI likha gaya", *[f"- {p}" for p in problems]]
    else:
        with open(MASTER, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader(); w.writerows(real)
        lines += ["", "Status: master.csv likha gaya (validation pass)."]
    if no_isin:
        lines += ["", "## Note: ISIN missing", *[f"- {s}" for s in no_isin[:50]]]
    os.makedirs(D, exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
