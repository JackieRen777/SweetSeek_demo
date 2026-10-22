from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: qa_substitute_docx_fonts.py INPUT.docx OUTPUT.docx")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    replacements = {
        "仿宋_GB2312": "STFangsong",
        "仿宋": "STFangsong",
        "黑体": "STHeiti",
        "宋体": "STSong",
    }
    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(output, "w") as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".xml"):
                text = data.decode("utf-8")
                for old, new in replacements.items():
                    text = text.replace(old, new)
                data = text.encode("utf-8")
            zout.writestr(item, data)


if __name__ == "__main__":
    main()
