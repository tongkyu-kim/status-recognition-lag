"""Build the Diplomatic White Paper text corpus (1990-2025) from the raw MOFA files.

Inputs : data/raw/kr_mofa/2026-09-30/white_papers/ (+ labels from metadata/download_log.csv)
Outputs: data/interim/text/white_papers/<file>.txt          one text file per raw file / zip member
         data/interim/text/white_papers_index.csv          year, label, method, chars, hangul chars
Methods: PDF -> pypdf with pdfminer fallback; HWP 5 -> built-in extractor; old HWP, .doc and .doc
inside zips -> LibreOffice headless (`soffice --convert-to txt`). Image-only scans stay empty
(status `needs_ocr`). Raw files are only read, never modified (inputs are copied to a temp dir).
"""

import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import _bootstrap  # noqa: F401
import pandas as pd

from srl.acquisition.extract import sniff_and_extract
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import write_table
from srl.utils.paths import project_root

SOFFICE = Path(os.environ.get("SOFFICE", r"C:\Program Files\LibreOffice\program\soffice.exe"))


def hangul(t: str) -> int:
    return sum("가" <= c <= "힣" for c in t)


def soffice_text(src: Path, work: Path) -> str:
    dst = work / ("in" + src.suffix.lower())
    shutil.copy(src, dst)
    subprocess.run(
        [
            str(SOFFICE),
            "--headless",
            "--convert-to",
            "txt:Text (encoded):UTF8",
            "--outdir",
            str(work),
            str(dst),
        ],
        capture_output=True,
        timeout=600,
    )
    out = work / "in.txt"
    text = out.read_text(encoding="utf-8-sig", errors="replace") if out.exists() else ""
    for f in (dst, out):
        f.unlink(missing_ok=True)
    return text


def zip_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & 0x800:  # UTF-8 flag set
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def main(args, logger) -> None:
    raw = get_path("data.raw") / "kr_mofa" / "2026-09-30" / "white_papers"
    out = get_path("data.interim") / "text" / "white_papers"
    out.mkdir(parents=True, exist_ok=True)
    labels = {}
    with (project_root() / "metadata" / "download_log.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if "white_papers" in r["dest"]:
                labels[os.path.basename(r["dest"])] = r["notes"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="srlwp") as tmp:
        work = Path(tmp)
        for f in sorted(raw.iterdir()):
            label = labels.get(f.name, f.name)
            ext = f.suffix.lower()
            members = []
            if ext == ".zip":
                with zipfile.ZipFile(f) as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue
                        name = zip_name(info)
                        p = work / f"member{len(members)}{Path(name).suffix.lower()}"
                        p.write_bytes(z.read(info))
                        members.append((p, f"{label} :: {name}", f"{f.stem}__{len(members)}"))
            else:
                members = [(f, label, f.stem)]
            for path, lab, stem in members:
                method, text = "none", ""
                suf = path.suffix.lower()
                if suf in (".pdf", ".hwp", ".hwpx", ".docx"):
                    fmt, text = sniff_and_extract(path)
                    method = fmt
                    if text.startswith("__EXTRACTION_ERROR__") or (suf == ".hwp" and not text):
                        text, method = soffice_text(path, work), "libreoffice"
                elif suf in (".doc", ".rtf", ".odt"):
                    text, method = soffice_text(path, work), "libreoffice"
                h = hangul(text)
                status = "text" if h > 300 else ("needs_ocr" if suf == ".pdf" else "conversion_failed")
                (out / f"{stem}.txt").write_text(text, encoding="utf-8")
                m = re.search(r"(19|20)\d\d", lab)
                rows.append(
                    {
                        "file": f.name,
                        "text_file": f"{stem}.txt",
                        "label": lab,
                        "year": int(m.group(0)) if m else None,
                        "method": method,
                        "chars": len(text),
                        "hangul_chars": h,
                        "status": status,
                    }
                )
                if path.parent == work:
                    path.unlink(missing_ok=True)
    idx = pd.DataFrame(rows)
    write_table(idx, get_path("data.interim") / "text" / "white_papers_index.csv")
    logger.info("status: %s", idx["status"].value_counts().to_dict())
    logger.info(
        "by year (text files / all):\n%s",
        idx.groupby("year")["status"].apply(lambda s: f"{(s == 'text').sum()}/{len(s)}").to_string(),
    )


if __name__ == "__main__":
    run_step("convert_white_papers", main, argparse.ArgumentParser(description=__doc__))
