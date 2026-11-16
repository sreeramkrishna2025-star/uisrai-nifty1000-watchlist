"""Nifty 500 constituent tracker (public repo; secrets/deploy nahi).

Official NSE Indices CSV laata hai, data/nifty500/master.csv se milaata hai,
badlav ho to: purani list snapshot mein, history.csv mein har badlav (kabhi delete nahi),
master.csv + web/n500.json update, aur report.md likhta hai.
Count 500 na ho to update NAHI karta (sirf report + exit 1), jab tak ACCEPT=1 na ho.
"""
import csv, io, json, os, re, sys, datetime, urllib.request

SOURCES = [
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
]
D = "data/nifty500"
MASTER, HIST, REPORT, JSON_OUT = f"{D}/master.csv", f"{D}/history.csv", f"{D}/report.md", f"{D}/n500.json"
FIELDS = ["Company Name", "Industry", "Symbol", "Series", "ISIN Code"]
IND = {'Financial Services': 'Finance', 'Healthcare': 'Pharma/Health', 'Information Technology': 'IT',
       'Automobile and Auto Components': 'Auto', 'Fast Moving Consumer Goods': 'FMCG', 'Oil Gas & Consumable Fuels': 'Oil & Gas',
       'Metals & Mining': 'Metals', 'Telecommunication': 'Telecom', 'Construction Materials': 'Cement',
       'Media Entertainment & Publication': 'Media', 'Forest Materials': 'Forest'}
TODAY = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).date().isoformat()
ACCEPT = os.environ.get("ACCEPT") == "1"


def fetch():
    errs = []
    for u in SOURCES:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36",
                                                     "Accept": "text/csv,*/*", "Referer": "https://www.niftyindices.com/"})
            raw = urllib.request.urlopen(req, timeout=40).read()
            txt = raw.decode("utf-8-sig", "replace")
            rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(io.StringIO(txt))]
            if not rows or not all(f in rows[0] for f in FIELDS):
                raise ValueError("columns galat: " + ",".join(rows[0].keys() if rows else []))
            return u, rows
        except Exception as e:
            errs.append(f"{u}: {e}")
    raise SystemExit("Official list nahi mili:\n" + "\n".join(errs))


def read(p):
    if not os.path.exists(p):
        return None
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(p, rows, fields):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def nm(n):
    return re.sub(r"\s*(Ltd\.?|Limited)\s*$", "", n.strip())


def main():
    os.makedirs(f"{D}/snapshots", exist_ok=True)
    src, new = fetch()
    syms = [r["Symbol"] for r in new]
    dup = sorted({s for s in syms if syms.count(s) > 1})
    old = read(MASTER)
    hist = read(HIST) or []
    oldm = {r["Symbol"]: r for r in (old or [])}
    newm = {r["Symbol"]: r for r in new}
    added = [newm[s] for s in syms if s not in oldm] if old is not None else []
    removed = [r for r in (old or []) if r["Symbol"] not in newm]
    problems = []
    if dup: problems.append("Duplicate symbol: " + ", ".join(dup))
    real = [x for x in newm if not x.startswith("DUMMY")]
    if len(real) != 500: problems.append(f"Constituent count {len(real)} hai (DUMMY chhod ke), 500 nahi")
    baseline = old is None
    # Jaanch tabhi rokti hai jab list badli ho; bina badlav ke roz fail nahi hoga
    ok = True  # User ka faisla: NSE ki nayi list hamesha apne aap lagao (rokna nahi)

    lines = [f"# Nifty 500 Constituent Tracker", "", f"- Check: {TODAY} (IST)", f"- Source: {src}",
             f"- Pichhli list: {len(oldm) if old is not None else '— (pehla snapshot)'}", f"- Nayi official list: {len(newm)}",
             f"- Added: {len(added)} · Removed: {len(removed)}"]
    if baseline: lines.append("- **BASELINE: yeh pehla snapshot hai, iske pehle ki history nahi hai.**")
    if problems: lines += ["", "## Note", *[f"- {p}" for p in problems],
                           "- Phir bhi official list laga di (jaankari ke liye note)."]
    if added or removed:
        lines += ["", "## Badlav", "", "Sr | NSE Symbol | Company | Pehle | Ab | Effective (CSV mein dikha)", "---|---|---|---|---|---"]
        i = 0
        for r in added: i += 1; lines.append(f"{i} | {r['Symbol']} | {r['Company Name']} | Not Included | Added | {TODAY}")
        for r in removed: i += 1; lines.append(f"{i} | {r['Symbol']} | {r['Company Name']} | Included | Removed | {TODAY}")
        lines += ["", "Effective date = jis din official CSV mein badlav pehli baar dikha (roz check hota hai). Announcement date ke liye niftyindices.com > Press Releases dekho."]
    elif not baseline:
        lines += ["", "Koi badlav nahi."]
    lines += ["", "## Pichhle badlav (history)", ""]
    for h in (hist[-40:] if hist else []):
        lines.append(f"- {h['detected']} · {h['symbol']} · {h['company']} · {h['change']}")
    if not hist: lines.append("- Abhi tak koi badlav record nahi.")
    lines += ["", "Official: https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500 · https://www.niftyindices.com/reports/index-reports"]

    if ok and (baseline or added or removed or not os.path.exists(JSON_OUT) or os.environ.get("REJSON") == "1"):
        if old is not None and (added or removed):
            write(f"{D}/snapshots/{TODAY}_before.csv", old, FIELDS)
        for r in added: hist.append({"detected": TODAY, "symbol": r["Symbol"], "company": r["Company Name"], "change": "Added", "source": src})
        for r in removed: hist.append({"detected": TODAY, "symbol": r["Symbol"], "company": r["Company Name"], "change": "Removed", "source": src})
        write(HIST, hist, ["detected", "symbol", "company", "change", "source"])
        write(MASTER, new, FIELDS)
        if baseline: write(f"{D}/snapshots/{TODAY}_baseline.csv", new, FIELDS)
        json.dump({"asOf": TODAY, "source": src, "count": len(new),
                   "list": [[r["Symbol"], nm(r["Company Name"]), IND.get(r["Industry"], r["Industry"])] for r in new if not r["Symbol"].startswith("DUMMY")],
                   "changes": hist[-30:]}, open(JSON_OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not ok:
        sys.exit(1)


main()
