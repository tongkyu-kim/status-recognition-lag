"""Acquire Korea Eximbank overseas direct investment (ODI) reports from data.go.kr file dataset 3040164.

Dataset: 한국수출입은행_해외직접투자 통계 (https://www.data.go.kr/data/3040164/fileData.do), licence
"이용허락범위 제한 없음" (no restriction), free. The current release plus the page's
"주기성 과거 데이터" list (quarterly/annual reports back to 2008) are downloaded through the same
anonymous flow the page uses:
    POST /tcs/dss/selectFileDataDownload.do -> atchFileId
    POST /cmm/cmm/check-limit.json          -> if needCaptcha: STOP (manual task, never bypassed)
    GET  /cmm/cmm/fileDownload.do
Files are reports (HWP/HWPX/PDF) with tables by region, country (major destinations), industry,
investor size and equity share; they are NOT a full country x year database.
"""

import argparse
import io
import re
import zipfile
from collections import Counter

import _bootstrap  # noqa: F401
from bs4 import BeautifulSoup

from srl.acquisition.fetch import PoliteSession, log_download, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "fdi_korea"
BASE = "https://www.data.go.kr"
PAGE = f"{BASE}/data/3040164/fileData.do"
PK = "3040164"
CURRENT_DETAIL_PK = "uddi:a056c56d-2774-442b-9b77-8c7a26648baf"
EXT = {b"PK\x03\x04": "hwpx", b"\xd0\xcf\x11\xe0": "hwp", b"%PDF": "pdf"}


def sniff_ext(data: bytes) -> str:
    """File type from content: zip containers are told apart (DOCX vs HWPX)."""
    if data[:4] == b"PK\x03\x04":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except zipfile.BadZipFile:
            return "zip"
        return (
            "docx"
            if "word/document.xml" in names
            else "hwpx"
            if any(n.startswith("Contents/") for n in names)
            else "zip"
        )
    return EXT.get(data[:4], "bin")


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval)
    hdr = {"X-Requested-With": "XMLHttpRequest", "Referer": PAGE}
    sess.get(PAGE)
    hist = sess.post(
        f"{BASE}/tcs/dss/selectHistAndCsvData.do",
        data={"publicDataPk": PK, "publicDataDetailPk": CURRENT_DETAIL_PK},
        headers=hdr,
    )
    items = [(CURRENT_DETAIL_PK, "1", "current")]
    for a in BeautifulSoup(hist.text, "lxml").select("a.openFileDetailPopup[data-public-pk]"):
        items.append((a["data-public-pk"], a.get("data-public-detail-sn", "1"), a.get_text(" ", strip=True)))
    logger.info("releases listed: %d (current + %d past)", len(items), len(items) - 1)
    got = skipped = 0
    counts = Counter(label for _, _, label in items)
    for detail_pk, _sn, label in items:
        slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", label).strip("_")[:60]
        if label == "current":  # name the current release by its title (e.g. ..._20260630), not "current"
            info = sess.post(
                f"{BASE}/tcs/dss/selectFileDataDownload.do",
                data={
                    "publicDataDetailPk": detail_pk,
                    "publicDataPk": PK,
                    "atchFileId": "",
                    "fileDetailSn": "1",
                    "publicDataTyCode": "PR0051",
                },
                headers=hdr,
            ).json()
            slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", info["dataSetFileDetailInfo"]["dataNm"]).strip("_")[:60]
        if counts[label] > 1:  # the history lists some names twice with DIFFERENT files
            slug += "_" + re.sub(r"\W", "", detail_pk.split(":")[-1])[:8]
        exts = ("hwpx", "hwp", "pdf", "docx", "zip", "bin")
        if any(raw_exists(SOURCE_ID, f"reports/{slug}.{e}") for e in exts):
            skipped += 1
            continue
        r = sess.post(
            f"{BASE}/tcs/dss/selectFileDataDownload.do",
            data={
                "publicDataDetailPk": detail_pk,
                "publicDataPk": PK,
                "atchFileId": "",
                "fileDetailSn": "1",
                "publicDataTyCode": "PR0051",
            },
            headers=hdr,
        )
        try:
            j = r.json()
        except ValueError:
            logger.error("%s: no JSON (%s)", label, r.status_code)
            continue
        if not j.get("status"):
            logger.error("%s: %s", label, j.get("error"))
            continue
        aid, fsn = j.get("atchFileId"), j.get("fileDetailSn")
        if not aid:  # 2008-2014 releases (DATY04) have no attached file on the portal any more
            log_download(SOURCE_ID, PAGE, outcome="no_file_attached", notes=f"{label} | detailPk {detail_pk}")
            logger.warning("%s: no file attached on data.go.kr (skipped)", label)
            continue
        resp = sess.post(
            f"{BASE}/cmm/cmm/check-limit.json", data={"atchFileId": aid, "fileDetailSn": fsn}, headers=hdr
        )
        try:
            lim = resp.json()
        except ValueError:  # an HTML page instead of JSON = throttling / block page: stop, never push on
            log_download(
                SOURCE_ID,
                PAGE,
                http_status=resp.status_code,
                outcome="limit_page",
                notes=f"non-JSON limit check at {label}: {resp.text[:150]!r}",
            )
            logger.warning("Limit check returned a non-JSON page at %s - stopping.", label)
            break
        if lim.get("needCaptcha"):
            log_download(SOURCE_ID, PAGE, outcome="captcha_required", notes=f"stopped at {label}")
            logger.warning("CAPTCHA requested at %s - stopping (manual task).", label)
            break
        url = f"{BASE}/cmm/cmm/fileDownload.do?atchFileId={aid}&fileDetailSn={fsn}"
        f = sess.get(url, headers={"Referer": PAGE})
        ext = sniff_ext(f.content)
        if f.status_code == 200 and len(f.content) > 1000:
            save_raw(
                SOURCE_ID,
                f"reports/{slug}.{ext}",
                f.content,
                url=url,
                http_status=200,
                notes=f"data.go.kr {PK} | {label} | detailPk {detail_pk}",
            )
            got += 1
    logger.info("downloaded %d, already present %d", got, skipped)
    write_folder_readme(
        SOURCE_ID,
        f"""
# Korea Eximbank overseas direct investment reports (data.go.kr file dataset {PK})

- Page: {PAGE} (licence: 이용허락범위 제한 없음; free). Current release + "주기성 과거 데이터".
- `reports/<release name>.<hwp|hwpx|pdf>`: quarterly and annual 해외직접투자 동향 reports. Each has
  tables by region, major destination countries, industry, investor size and equity share,
  typically covering the last 3 years + the reference quarter.
- `datagokr_3040164_history.html`: the past-version list as served. `koreaexim_odi_statistics_2026Q2.hwpx`:
  first manual-check download of the current release (same file as reports/..._20260630).
- Download flow mirrors the page's own button; the site's CAPTCHA limit check is honoured.
- Text extraction: srl.acquisition.extract.sniff_and_extract (HWP 5 / HWPX / DOCX / PDF), by content.
- KNOWN NAMING ISSUE: the 8 reports for 2008-2010 were saved with a `.hwpx` extension by the first
  run but are DOCX files (content-sniffed correctly by the extractor). Raw files are not renamed.
- Duplicate release names in the portal history (20131231, 20141231, 20170811) are different files;
  later copies are saved as `<name>_<id8>.<ext>`.
- The PI's manual downloads of 2026-09-30 (browser Downloads folder) were checked by SHA-256: all
  are byte-identical to files here, so none were deposited separately.
Script: scripts/acquire/acq_koreaexim_odi.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--interval", type=float, default=3.0)
    run_step("acq_koreaexim_odi", main, p)
