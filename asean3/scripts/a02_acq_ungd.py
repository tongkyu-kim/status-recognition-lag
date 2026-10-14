"""UN General Debate statements of ASEAN+3 members from gadebate.un.org (sessions 64-79, 2009-2024).

gadebate.un.org (UN DGACM General Debate site) allows these paths in robots.txt. Each country page
for a session links one or more statement PDFs (English and/or original language). Sessions 55-63
(2000-2008) are not on the site (404 for every probe); documents.un.org disallows /doc and /api, and
the UNGDC (Harvard Dataverse doi:10.7910/DVN/0TJX8Y, CC0) sits behind a guestbook, so those years
are a manual task (asean3/docs/manual_tasks.md).

Raw: data/raw/ungd_gadebate/<date>/pages/<session>_<iso>.html and pdf/<session>_<iso>__<file>.pdf
"""

from __future__ import annotations

import csv
import logging
import re

import _common as C
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme

SOURCE_ID = "ungd_gadebate"
BASE = "https://gadebate.un.org"
SLUGS = {"BRN": "brunei-darussalam", "KHM": "cambodia", "CHN": "china", "IDN": "indonesia",
         "JPN": "japan", "KOR": "republic-korea", "LAO": "lao-peoples-democratic-republic",
         "MYS": "malaysia", "MMR": "myanmar", "PHL": "philippines", "SGP": "singapore",
         "THA": "thailand", "TLS": "timor-leste", "VNM": "viet-nam"}
SESSIONS = range(64, 80)  # session s opens in September of year 1945 + s

log = logging.getLogger("a02")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sess = PoliteSession(SOURCE_ID, min_interval=2.0)
    inv = []
    for s in SESSIONS:
        for iso, slug in SLUGS.items():
            url = f"{BASE}/en/{s}/{slug}"
            name = f"pages/{s}_{iso}.html"
            if raw_exists(SOURCE_ID, name):
                html = (raw_dir(SOURCE_ID) / name).read_text(encoding="utf-8", errors="replace")
                status = 200
            else:
                r = sess.get(url)
                status = r.status_code
                if status != 200:
                    log.warning("%s %s", url, status)
                    inv.append({"session": s, "year": 1945 + s, "iso3": iso, "page_url": url,
                                "page_status": status, "pdf_url": "", "pdf_file": "", "pdf_status": ""})
                    continue
                html = r.text
                save_raw(SOURCE_ID, name, r.content, url=url, http_status=status)
            pdfs = sorted(set(re.findall(r'href="(/sites/default/files/gastatements/[^"]+\.pdf)"', html)))
            if not pdfs:
                inv.append({"session": s, "year": 1945 + s, "iso3": iso, "page_url": url,
                            "page_status": status, "pdf_url": "", "pdf_file": "", "pdf_status": "no_pdf_link"})
            for p in pdfs:
                fname = f"pdf/{s}_{iso}__{p.rsplit('/', 1)[-1]}"
                pstat = "exists"
                if not raw_exists(SOURCE_ID, fname):
                    r = sess.get(BASE + p)
                    pstat = r.status_code
                    if r.status_code == 200 and r.content[:4] == b"%PDF":
                        save_raw(SOURCE_ID, fname, r.content, url=BASE + p, http_status=200)
                    else:
                        log.warning("%s %s", p, r.status_code)
                inv.append({"session": s, "year": 1945 + s, "iso3": iso, "page_url": url, "page_status": status,
                            "pdf_url": BASE + p, "pdf_file": fname, "pdf_status": pstat})
            log.info("session %s %s: %d pdf", s, iso, len(pdfs))
    out = C.INTERIM / "ungd_inventory.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(inv[0]))
        w.writeheader()
        w.writerows(inv)
    write_folder_readme(SOURCE_ID, f"""
# UN General Debate statements (gadebate.un.org), ASEAN+3, sessions 64-79 (2009-2024)

- Source: {BASE}/en/<session>/<country-slug>; statement PDFs as linked on each page.
- robots.txt permits these paths (checked 2026-10-14). Rate: 1 request / 2 s.
- Sessions 55-63 return 404 on this site; see asean3/docs/manual_tasks.md.
- Script: asean3/scripts/a02_acq_ungd.py; inventory: asean3/data/interim/ungd_inventory.csv
""")


if __name__ == "__main__":
    main()
