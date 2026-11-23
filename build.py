"""Build site/data.js from the repository data. No model is called; every string on the page comes from data/ or code."""
import json
from pathlib import Path

from signals import drafts as D
from signals import ledger as L
from signals import payload as P
from signals import rules

ROOT = Path(__file__).parent
led = L.build(L.load())
drafts = D.load_drafts()
product = D.load_product()
PLACEHOLDER = "https://www.linkedin.com/in/chosen-in-sales-navigator"

accounts = []
for a in led["accounts"]:
    row = {k: a[k] for k in ("id", "employer", "status", "reason", "reason_text", "lead_page", "location")}
    row["pages"] = [{k: p[k] for k in ("id", "title", "url", "posted", "code", "quotes", "source", "http", "freshness")}
                    | {"why": ("Names Vista, inside the window." if p["code"] in ("names_vista", "migrating_to_vista")
                           else "Same employer, merged into this account; this ad does not name Vista itself." if a["status"] == "matched" and p["code"] == "no_vista"
                           else L.page_reason(p, a["employer"]))}
                    for p in a["pages"]]
    if a["status"] == "matched":
        d = drafts["accounts"][a["id"]]
        D.render(a, led, "Alexandria")  # refuses to build if a draft fails its own facts
        row["drafts"] = {k: d[k] for k in ("note", "followup_1", "followup_2")}
        row["approach"] = d["approach"]
        row["approach_quote"] = d["approach_quote"]
        row["sales_navigator"] = d["sales_navigator"]
        row["payload"] = P.heyreach(a, PLACEHOLDER)
    accounts.append(row)

out = {"read_on": led["read_on"], "window_days": led["window_days"], "counts": led["counts"], "proof": led["proof"],
       "accounts": accounts, "also_read": led["also_read"], "australia": led["australia"], "note_limit": rules.NOTE_LIMIT,
       "product_source": product["source"]}
(ROOT / "site").mkdir(exist_ok=True)
(ROOT / "site" / "data.js").write_text("window.LEDGER = " + json.dumps(out, indent=1, ensure_ascii=False) + ";\n")
print("site/data.js written:", led["counts"], "closes" if led["proof"]["closes"] else "DOES NOT CLOSE")

import re
import subprocess
import sys

res = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True)
m = re.search(r"(\d+) passed", res.stdout)
if res.returncode != 0 or not m:
    sys.exit("tests failing, page not built:\n" + res.stdout[-2000:])
with open(ROOT / "site" / "data.js", "a") as f:
    f.write(f'window.TESTS = "{m.group(1)} tests, all passing.";\n')
print(m.group(1), "tests passing")
