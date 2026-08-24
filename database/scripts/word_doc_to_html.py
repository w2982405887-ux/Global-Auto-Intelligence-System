from __future__ import annotations

import sys
from pathlib import Path

import pythoncom
import win32com.client


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python word_doc_to_html.py <input.doc> <output.html>")
        return 2

    src = str(Path(sys.argv[1]).resolve())
    dst = str(Path(sys.argv[2]).resolve())
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(
            FileName=src,
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Revert=False,
            NoEncodingDialog=True,
            OpenAndRepair=False,
        )
        doc.SaveAs2(FileName=dst, FileFormat=8, AddToRecentFiles=False)
        doc.Close(False)
        print(dst)
    finally:
        word.Quit()
        pythoncom.CoUninitialize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
