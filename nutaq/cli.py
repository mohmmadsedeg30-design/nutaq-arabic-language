"""واجهة سطر أوامر لغة نُطْق."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import Lexer, NutaqError, parse, run


VERSION = "0.3.0"


def repl() -> int:
    print(f"نُطْق {VERSION} — اكتب «خروج» للإنهاء.")
    print("ملاحظة: الوضع التفاعلي مخصص للتعبيرات والتعليمات ذات السطر الواحد.")
    while True:
        try:
            source = input("نطق> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not source:
            continue
        if source in {"خروج", "exit", "quit"}:
            return 0
        try:
            result = run(source)
            if result is not None:
                print(f"=> {result}")
        except NutaqError as error:
            print(error, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nutaq",
        description="مفسّر لغة نُطْق البرمجية العربية.",
    )
    parser.add_argument("file", nargs="?", help="ملف مصدر بامتداد .نطق أو أي ملف نصي UTF-8")
    parser.add_argument("--تحقق", "--check", action="store_true", dest="check", help="تحليل الملف دون تشغيله")
    parser.add_argument("--رموز", "--tokens", action="store_true", dest="tokens", help="عرض الرموز المعجمية دون تشغيله")
    parser.add_argument("--إصدار", "--version", action="version", version=f"نُطْق {VERSION}")
    args = parser.parse_args(argv)

    if not args.file:
        return repl()

    path = Path(args.file)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"خطأ_ملف: تعذر قراءة «{path}»: {error}", file=sys.stderr)
        return 2

    try:
        if args.tokens:
            for token in Lexer(source).scan_tokens():
                shown = token.value.replace("\n", "\\n")
                print(f"{token.line}:{token.column}\t{token.kind}\t{shown}")
            return 0
        if args.check:
            parse(source)
            print(f"الملف «{path.name}» صحيح نحويًا.")
            return 0
        run(source, project_dir=path.parent)
        return 0
    except NutaqError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
