#!/usr/bin/env bash
# docx -> PDF программно, без Microsoft Word и без GUI:
#   pandoc (docx -> HTML) + weasyprint (HTML -> PDF, движок pango/cairo из Homebrew).
# Usage: scripts/docx_to_pdf.sh <in.docx> <out.pdf>
# Prints "ok <out.pdf> pages=N" or fails with a reason.
set -euo pipefail
in="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
out="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
[ -f "$in" ] || { echo "FAIL: input not found: $in" >&2; exit 1; }
command -v pandoc >/dev/null || { echo "FAIL: pandoc not installed (brew install pandoc)" >&2; exit 1; }
command -v uv >/dev/null || { echo "FAIL: uv not installed" >&2; exit 1; }
[ -d /opt/homebrew/lib ] && export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"

work="$(dirname "$out")/.docx2pdf-$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

pandoc "$in" -s -t html5 -o "$work/doc.html" --metadata title=" " 2>/dev/null
# pandoc вставляет <header id="title-block-header"> под пустой title — убрать.
perl -0pi -e 's/<header id="title-block-header">.*?<\/header>//s' "$work/doc.html"

cat > "$work/style.css" <<'CSS'
@page { size: A4; margin: 20mm 15mm 20mm 25mm; }
html { font-family: "Times New Roman", "Liberation Serif", serif; font-size: 11pt; line-height: 1.25; }
body { max-width: none; margin: 0; padding: 0; }
p { margin: 0 0 4pt 0; text-align: justify; }
h1, h2, h3, h4 { font-size: 12pt; font-weight: bold; text-align: center; margin: 10pt 0 6pt 0; }
h1 { font-size: 13pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
tr { page-break-inside: avoid; }
td, th { border: 1px solid #000; padding: 3pt 4pt; vertical-align: top; font-size: 10.5pt; text-align: left; }
ul, ol { margin: 0 0 4pt 0; }
a { color: inherit; text-decoration: underline; }
CSS

rm -f "$out"
uv run --no-project --with weasyprint --with pypdf python - "$work/doc.html" "$work/style.css" "$out" <<'PY'
import sys
from weasyprint import HTML, CSS
from pypdf import PdfReader
html, css, out = sys.argv[1:4]
HTML(html).write_pdf(out, stylesheets=[CSS(filename=css)])
print(f"ok {out} pages={len(PdfReader(out).pages)}")
PY
