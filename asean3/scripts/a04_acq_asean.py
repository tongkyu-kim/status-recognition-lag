"""ASEAN Plus Three institutional statements from asean.org (robots.txt is empty: no restriction).

Discovery: the site's WordPress/Yoast sitemaps (post- and page-sitemaps). A URL is in the frame if its
slug names ASEAN Plus Three (plus-three / apt) and one of: summit, economic ministers, joint
statement/media statement, chairman's statement, declaration, cooperation work plan. Each matched page
is saved, and PDFs it links on asean.org/wp-content are saved too.

These are jointly negotiated documents: they give regional context only and are never attributed
to a single government (asean3/docs/source_rules.md).

Raw: data/raw/asean_apt/<date>/sitemaps/*.xml, pages/<slug>.html, pdf/<name>.pdf
"""

from __future__ import annotations

import csv
import hashlib
import logging
import re

import _common as C
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme

SOURCE_ID = "asean_apt"
SITEMAP_INDEX = "https://asean.org/wp-sitemap.xml"
APT = re.compile(r"(plus-three|plus-3|\bapt\b|-apt-|asean3|asean-3)", re.I)
KIND = re.compile(r"(summit|economic-minister|aem|ministers|joint-statement|media-statement|chairman|"
                  r"chairs-statement|declaration|work-plan|cooperation)", re.I)

log = logging.getLogger("a04")


def short(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1][:90]
    return f"{slug}_{hashlib.sha1(url.encode()).hexdigest()[:6]}"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sess = PoliteSession(SOURCE_ID, min_interval=1.5)
    idx = sess.get(SITEMAP_INDEX)
    save_raw(SOURCE_ID, "sitemaps/index.xml", idx.content, url=SITEMAP_INDEX, http_status=idx.status_code)
    maps = re.findall(r"<loc>([^<]+)</loc>", idx.text)
    urls = []
    for m in maps:
        if not re.search(r"(post|page)-sitemap", m):
            continue
        name = "sitemaps/" + m.rsplit("/", 1)[-1]
        if raw_exists(SOURCE_ID, name):
            txt = (raw_dir(SOURCE_ID) / name).read_text(encoding="utf-8")
        else:
            r = sess.get(m)
            save_raw(SOURCE_ID, name, r.content, url=m, http_status=r.status_code)
            txt = r.text
        urls += re.findall(r"<loc>([^<]+)</loc>", txt)
    hits = sorted({u for u in urls if APT.search(u) and KIND.search(u)})
    log.info("%d sitemap URLs, %d APT candidates", len(urls), len(hits))
    inv = []
    for u in hits:
        name = f"pages/{short(u)}.html"
        if raw_exists(SOURCE_ID, name):
            html = (raw_dir(SOURCE_ID) / name).read_text(encoding="utf-8", errors="replace")
            st = 200
        else:
            r = sess.get(u)
            st = r.status_code
            if st != 200:
                inv.append({"url": u, "status": st, "file": "", "pdf_url": "", "pdf_file": ""})
                continue
            save_raw(SOURCE_ID, name, r.content, url=u, http_status=st)
            html = r.text
        pdfs = sorted(set(re.findall(r'href="(https://asean\.org/wp-content/uploads/[^"]+\.pdf)"', html)))
        if not pdfs:
            inv.append({"url": u, "status": st, "file": name, "pdf_url": "", "pdf_file": ""})
        for p in pdfs:
            pname = f"pdf/{short(p)}.pdf"
            if not raw_exists(SOURCE_ID, pname):
                r = sess.get(p)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    save_raw(SOURCE_ID, pname, r.content, url=p, http_status=200)
                else:
                    pname = f"FAILED_{r.status_code}"
            inv.append({"url": u, "status": st, "file": name, "pdf_url": p, "pdf_file": pname})
    with (C.INTERIM / "asean_apt_inventory.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["url", "status", "file", "pdf_url", "pdf_file"])
        w.writeheader()
        w.writerows(inv)
    write_folder_readme(SOURCE_ID, f"""
# ASEAN Plus Three statements (asean.org)

- Discovery via {SITEMAP_INDEX} (post/page sitemaps); slug filters APT={APT.pattern} and KIND={KIND.pattern}.
- robots.txt on asean.org is empty (checked 2026-10-14). Rate 1 request / 1.5 s.
- Joint documents: regional context only; never attributed to one government.
- Script: asean3/scripts/a04_acq_asean.py; inventory asean3/data/interim/asean_apt_inventory.csv
""")


if __name__ == "__main__":
    main()
