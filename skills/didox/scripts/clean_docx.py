#!/usr/bin/env -S uv run --no-project python
"""Accept all tracked changes and strip all comments from a .docx.

Usage:
    uv run --no-project scripts/clean_docx.py <in.docx> <out.docx>

Exit 0 and prints "ok <out> ins=0 del=0 comments=0" on success.
Exit 1 with a reason if the result still contains revisions/comments.
"""
import re
import sys
import zipfile

REV_TAGS = ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange",
            "tcPrChange", "tblGridChange", "numberingChange")


def clean_xml(xml: str) -> str:
    # accept insertions: unwrap <w:ins ...>...</w:ins>
    xml = re.sub(r"<w:ins\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:ins\b[^>]*>", "", xml)
    xml = xml.replace("</w:ins>", "")
    # accept deletions: drop <w:del ...>...</w:del> and self-closing marks
    xml = re.sub(r"<w:del\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:del\b[^>]*>.*?</w:del>", "", xml, flags=re.S)
    # moves: drop moveFrom, unwrap moveTo
    xml = re.sub(r"<w:moveFrom\b[^>]*>.*?</w:moveFrom>", "", xml, flags=re.S)
    xml = re.sub(r"<w:moveTo\b[^>]*>", "", xml)
    xml = xml.replace("</w:moveTo>", "")
    xml = re.sub(r"<w:move(?:From|To)Range(?:Start|End)\b[^>]*/>", "", xml)
    # formatting-change records
    for tag in REV_TAGS:
        xml = re.sub(rf"<w:{tag}\b[^>]*>.*?</w:{tag}>", "", xml, flags=re.S)
        xml = re.sub(rf"<w:{tag}\b[^>]*/>", "", xml)
    # comments: range markers and the reference runs
    xml = re.sub(r"<w:commentRange(?:Start|End)\b[^>]*/>", "", xml)
    xml = re.sub(r"<w:r\b[^>]*>(?:(?!</w:r>).)*?<w:commentReference\b[^>]*/>(?:(?!</w:r>).)*?</w:r>",
                 "", xml, flags=re.S)
    xml = re.sub(r"<w:commentReference\b[^>]*/>", "", xml)
    return xml


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    zin = zipfile.ZipFile(src)
    zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        name = item.filename
        if name.startswith("word/comments"):
            continue  # comments.xml, commentsExtended.xml, commentsIds.xml, ...
        data = zin.read(name)
        if name == "word/document.xml" or re.match(r"word/(header|footer|footnotes|endnotes)\d*\.xml", name):
            data = clean_xml(data.decode("utf-8")).encode("utf-8")
        elif name == "word/_rels/document.xml.rels":
            data = re.sub(r'<Relationship\b[^>]*Target="comments[^"]*"[^>]*/>', "", data.decode("utf-8")).encode("utf-8")
        elif name == "[Content_Types].xml":
            data = re.sub(r'<Override\b[^>]*PartName="/word/comments[^"]*"[^>]*/>', "", data.decode("utf-8")).encode("utf-8")
        elif name == "word/settings.xml":
            data = re.sub(r"<w:trackRevisions\b[^>]*/>", "", data.decode("utf-8")).encode("utf-8")
        zout.writestr(item, data)
    zout.close()

    # verify
    doc = zipfile.ZipFile(dst).read("word/document.xml").decode("utf-8")
    ins = len(re.findall(r"<w:ins\b", doc))
    dele = len(re.findall(r"<w:del\b", doc))
    com = len(re.findall(r"<w:comment", doc)) + sum(1 for n in zipfile.ZipFile(dst).namelist() if n.startswith("word/comments"))
    if ins or dele or com:
        print(f"FAIL {dst}: ins={ins} del={dele} comments={com}", file=sys.stderr)
        return 1
    print(f"ok {dst} ins=0 del=0 comments=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
