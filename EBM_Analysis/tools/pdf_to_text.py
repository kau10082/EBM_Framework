# -*- coding: utf-8 -*-
"""無 API：把 inputs/ 的 PDF 抽成純文字到 cache/{stem}.txt，供我（Claude）讀取評讀。
（在 Claude Code/Cowork 內，我也可直接用 Read 工具讀 PDF；此工具用於批次預抽或抽取品質檢查。）

  python tools/pdf_to_text.py            # 抽 inputs/ 全部
  python tools/pdf_to_text.py a.pdf b.pdf
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
INPUTS = ROOT / "inputs"
CACHE = ROOT / "cache"
MIN_CHARS = 400


def extract(path):
    path = str(path)
    try:
        import fitz
        doc = fitz.open(path)
        try:
            return "\n".join(p.get_text() for p in doc)
        finally:
            doc.close()
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    except Exception:
        return ""


def main(argv):
    CACHE.mkdir(exist_ok=True)
    pdfs = [Path(a) for a in argv] if argv else sorted(INPUTS.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs（{INPUTS}）")
        return
    for pdf in pdfs:
        text = extract(pdf)
        n = len(text.strip())
        if n < MIN_CHARS:
            print(f"⚠️ {pdf.name}: {n} 字 → needs_OCR（無文字層？）")
            continue
        (CACHE / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
        print(f"✓ {pdf.name} → cache/{pdf.stem}.txt（{n} 字）")


if __name__ == "__main__":
    main(sys.argv[1:])
