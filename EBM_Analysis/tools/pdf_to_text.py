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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import workdir  # noqa: E402  執行期資料導向工作夾（見 workdir.py）
INPUTS = Path(workdir.inputs_dir())
CACHE = Path(workdir.cache_dir())
MIN_CHARS = 400


def extract(path):
    """回 (text, err)：err=None 正常；err 非 None＝抽取失敗原因（缺依賴/壞檔）≠『無文字層』。"""
    path = str(path)
    engines = 0
    err = None
    try:
        import fitz
        engines += 1
        doc = fitz.open(path)
        try:
            return "\n".join(p.get_text() for p in doc), None
        finally:
            doc.close()
    except ImportError:
        pass
    except Exception as e:
        err = f"fitz 解析失敗：{str(e)[:60]}"
    try:
        from pypdf import PdfReader
        engines += 1
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages), None
    except ImportError:
        pass
    except Exception as e:
        err = f"pypdf 解析失敗：{str(e)[:60]}"
    if engines == 0:
        return "", "pymupdf 與 pypdf 皆未安裝（pip install pymupdf 或 pypdf）——非 PDF 無文字層"
    return "", err or "抽取失敗"


def main(argv):
    CACHE.mkdir(exist_ok=True)
    pdfs = [Path(a) for a in argv] if argv else sorted(INPUTS.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs（{INPUTS}）")
        return
    for pdf in pdfs:
        text, err = extract(pdf)
        n = len(text.strip())
        if err:
            print(f"❌ {pdf.name}: 抽取失敗（{err}）——與『無文字層 needs_OCR』不同，修復環境/檔案後重跑")
            continue
        if n < MIN_CHARS:
            print(f"⚠️ {pdf.name}: {n} 字 → needs_OCR（無文字層？）")
            continue
        (CACHE / f"{pdf.stem}.txt").write_text(text, encoding="utf-8")
        print(f"✓ {pdf.name} → cache/{pdf.stem}.txt（{n} 字）")


if __name__ == "__main__":
    main(sys.argv[1:])
