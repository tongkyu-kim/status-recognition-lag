"""Parse Korea Eximbank quarterly/annual ODI reports into a country x period table.

Input : data/raw/fdi_korea/<date>/reports/*  (HWPX / DOCX, data.go.kr dataset 3040164)
Output: data/interim/prelim/odi_korea_reports_long.csv      every parsed table cell (provenance)
        data/interim/prelim/odi_korea_country_year.csv      annual values per partner, latest report wins
        outputs/diagnostics/odi_reports_parse_log.csv       per report: tables / rows parsed

Parsing rule (text extracted cell-by-cell): a table header "구 분" (or "구분") is followed by period
labels ("2023년", "2025.2Q", "2025.1~6월", "증감률" ...); each data row is a name line followed by as
many value lines as there are labels. Only rows whose name is a panel partner are kept. Values are
the reports' own units (typically US$ million, gross investment 총투자 basis) - the unit line found
above the table is recorded. Values revised across reports are kept in the long file; the
country-year file takes the most recent report and records the spread across reports.
"""

import argparse
import re

import _bootstrap  # noqa: F401
import pandas as pd

from srl.acquisition.extract import sniff_and_extract
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import write_table

NAMES = {
    "중국": "CHN",
    "베트남": "VNM",
    "인도네시아": "IDN",
    "싱가포르": "SGP",
    "말레이시아": "MYS",
    "태국": "THA",
    "필리핀": "PHL",
    "캄보디아": "KHM",
    "라오스": "LAO",
    "미얀마": "MMR",
    "브루나이": "BRN",
    "동티모르": "TLS",
    "홍콩": "HKG",
}
LABEL = re.compile(
    r"^(?:"
    r"(?:19|20)\d{2}\s*년?"  # 2016 / 2016년
    r"|(?:19|20)\d{2}\s*[.년]\s*[\d~\-]+\s*(?:월|분기|Q)?.*"  # 2025.2Q / 2025.1~6월
    r"|[‘'’`]\s*\d{2}\s*[.년]\s*[\d~\-]+\s*(?:월|분기|Q)?.*"  # ‘18.2Q / ’19.1~6월
    r"|(?:19|20)\d{2}\s*[.년]?\s*[1-4]\s*/\s*4\s*분기?"  # 2008년 2/4분기
    r"|증감률|증감|비중|누계|구성비|전년동기.*|전기.*"
    r")$"
)
NUM = re.compile(r"^△?-?[\d,]+(?:\.\d+)?%?$")


def to_number(cell: str) -> float | None:
    c = cell.replace(",", "").replace("%", "")
    neg = c.startswith("△") or c.startswith("-")
    c = c.lstrip("△-")
    try:
        v = float(c)
    except ValueError:
        return None
    return -v if neg else v


INDUSTRY = re.compile(
    r"제조|금융|보험|부동산|정보통신|도소매|도·소매|광업|과학|숙박|건설|운수|전기|서비스|농림|어업"
)


def report_period(name: str, text: str = "") -> str:
    m = re.search(r"(20\d{2})\s*년\s*(\d)\s*분기", text[:300]) if not re.search(r"20\d{2}", name) else None
    if m:  # e.g. current.hwpx -> "2026년 2분기"
        return f"{m.group(1)}-{int(m.group(2)) * 3:02d}-28"
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(20\d{2})년_?(\d)_4분기", name)
    if m:
        return f"{m.group(1)}-{int(m.group(2)) * 3:02d}-28"
    m = re.search(r"(20\d{2})년", name)
    return f"{m.group(1)}-12-31" if m else ""


def parse(text: str) -> list[dict]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows, i, table_title, unit = [], 0, "", ""
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("[표") or "추이" in ln or "현황" in ln:
            table_title = ln[:80]
        if re.search(r"\((?:백만|천|억)\s*(?:달러|불)|단위", ln):
            unit = ln[:40]
        if re.fullmatch(r"구\s*분", ln):
            labels, j = [], i + 1
            while (
                j < len(lines)
                and LABEL.match(lines[j])
                and (not NUM.match(lines[j].replace(" ", "")) or re.fullmatch(r"(?:19|20)\d{2}", lines[j]))
            ):
                labels.append(re.sub(r"\s+", "", lines[j]))
                j += 1
            if len(labels) >= 2:
                k = j
                while (
                    k < len(lines)
                    and not lines[k].startswith("[표")
                    and not re.fullmatch(r"구\s*분", lines[k])
                ):
                    name = re.sub(r"\s+", "", lines[k])
                    vals = lines[k + 1 : k + 1 + len(labels)]
                    if len(vals) == len(labels) and all(NUM.match(v.replace(" ", "")) for v in vals):
                        if name in NAMES:
                            for lab, v in zip(labels, vals, strict=True):
                                rows.append(
                                    {
                                        "table": table_title,
                                        "unit_line": unit,
                                        "row_name": name,
                                        "iso3": NAMES[name],
                                        "label": lab,
                                        "value_raw": v,
                                        "value": to_number(v.replace(" ", "")),
                                    }
                                )
                        k += 1 + len(labels)
                    else:
                        k += 1
                        if k - j > 400:
                            break
                i = k
                continue
        i += 1
    return rows


def main(args, logger) -> None:
    raw = get_path("data.raw") / "fdi_korea"
    files = sorted(p for p in raw.glob("*/reports/*") if p.is_file())
    long, log = [], []
    for f in files:
        fmt, text = sniff_and_extract(f)
        rows = parse(text)
        for r in rows:
            r.update({"report_file": f.name, "report_date": report_period(f.name, text), "format": fmt})
        long += rows
        log.append(
            {
                "report_file": f.name,
                "format": fmt,
                "chars": len(text),
                "rows": len(rows),
                "partners": "|".join(sorted({r["iso3"] for r in rows})),
            }
        )
    df = pd.DataFrame(long)
    out = get_path("data.interim") / "prelim"
    write_table(pd.DataFrame(log), get_path("outputs.diagnostics", mkdir=True) / "odi_reports_parse_log.csv")
    if df.empty:
        logger.warning("nothing parsed")
        return
    write_table(df, out / "odi_korea_reports_long.csv")
    # total (all-industry) investment by destination: regional country tables, never industry tables
    regional = df["table"].str.contains("국가별", na=False) & ~df["table"].str.contains(INDUSTRY, na=False)
    ann = df[
        df["label"].str.fullmatch(r"(?:19|20)\d{2}년?") & regional & ~df["value_raw"].str.contains("%")
    ].copy()
    ann["year"] = ann["label"].str[:4].astype(int)
    ann = ann.sort_values("report_date")
    agg = (
        ann.groupby(["iso3", "year"])
        .agg(
            value_latest=("value", "last"),
            report_latest=("report_file", "last"),
            n_reports=("report_file", "nunique"),
            value_min=("value", "min"),
            value_max=("value", "max"),
            unit_line=("unit_line", "last"),
            table=("table", "last"),
        )
        .reset_index()
    )
    agg["revised_across_reports"] = agg["value_min"] != agg["value_max"]
    write_table(agg, out / "odi_korea_country_year.csv")
    logger.info(
        "parsed %d cells from %d reports; annual country-years: %d\n%s",
        len(df),
        len(files),
        len(agg),
        agg.pivot(index="year", columns="iso3", values="value_latest").tail(25).to_string(),
    )


if __name__ == "__main__":
    run_step("build_odi_reports", main, argparse.ArgumentParser(description=__doc__))
