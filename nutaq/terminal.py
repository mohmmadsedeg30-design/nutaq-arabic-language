"""مكتبة الطرفية العربية للغة نُطْق.

تستخدم ANSI ومكتبة بايثون القياسية فقط، لذا تناسب Termux والطرفيات الحديثة.
"""
from __future__ import annotations

import shutil
import time
from typing import Any

from .core import Call, Interpreter


RESET = "\033[0m"
COLORS = {
    "رمادي": "\033[90m",
    "أحمر": "\033[91m",
    "أخضر": "\033[92m",
    "أصفر": "\033[93m",
    "أزرق": "\033[94m",
    "أرجواني": "\033[95m",
    "سماوي": "\033[96m",
    "أبيض": "\033[97m",
}


def _color(interpreter: Interpreter, value: Any, color: Any, node: Call) -> str:
    if not isinstance(color, str) or color not in COLORS:
        interpreter.error(node, "اللون غير معروف. الألوان المتاحة: " + "، ".join(COLORS))
    return COLORS[color] + interpreter.format_value(value) + RESET


def _dimensions() -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns, size.lines


def install_terminal_builtins(interpreter: Interpreter) -> None:
    """يسجل دوال الطرفية العربية ويُبقيها خفيفة وقابلة للاختبار."""

    def color(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        return _color(interpreter, args[0], args[1], node)

    def clear(_args: list[Any], _interpreter: Interpreter, _node: Call) -> None:
        interpreter.raw_output("\033[2J\033[H")
        return None

    def wait(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        seconds = args[0]
        if not interpreter.is_number(seconds) or seconds < 0:
            interpreter.error(node, "مدة «انتظر» يجب أن تكون عددًا غير سالب.")
        time.sleep(seconds)
        return None

    def width(_args: list[Any], _interpreter: Interpreter, _node: Call) -> int:
        return _dimensions()[0]

    def height(_args: list[Any], _interpreter: Interpreter, _node: Call) -> int:
        return _dimensions()[1]

    def dimensions(_args: list[Any], _interpreter: Interpreter, _node: Call) -> dict[str, int]:
        columns, lines = _dimensions()
        return {"عرض": columns, "ارتفاع": lines}

    def repeat(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        amount = interpreter.require_integer(node, args[1], "عدد مرات التكرار")
        if amount < 0:
            interpreter.error(node, "عدد مرات التكرار يجب أن يكون غير سالب.")
        return interpreter.format_value(args[0]) * amount

    def write(args: list[Any], _interpreter: Interpreter, _node: Call) -> None:
        ending = args[1] if len(args) == 2 else ""
        if not isinstance(ending, str):
            interpreter.error(_node, "نهاية «اكتب» يجب أن تكون نصًا.")
        interpreter.write_terminal(interpreter.format_value(args[0]))
        interpreter.raw_output(ending)
        return None

    def right_text(args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        return "\u2067" + interpreter.format_value(args[0]) + "\u2069"

    def print_right(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        text = interpreter.format_value(args[0])
        if len(args) == 2:
            text = _color(interpreter, text, args[1], node)
        width_value, _ = _dimensions()
        # يتحسب العرض تقريبيًا، وهو ملائم للنص العربي البسيط وتوافق الطرفيات المختلفة.
        visible = len(interpreter.format_value(args[0]))
        padding = " " * max(0, width_value - visible)
        interpreter.output(interpreter.terminal_text(padding + text))
        return None

    def input_right(args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        prompt = interpreter.format_value(args[0]) if args else ""
        return interpreter.input_provider("\u2067" + prompt + "\u2069")

    def exit_program(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        code = interpreter.require_integer(node, args[0], "حالة الخروج") if args else 0
        if code < 0:
            interpreter.error(node, "حالة الخروج يجب أن تكون غير سالبة.")
        raise SystemExit(code)

    def line(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        character = args[0] if args else "─"
        amount = args[1] if len(args) == 2 else _dimensions()[0]
        if not isinstance(character, str) or not character:
            interpreter.error(node, "رمز الخط يجب أن يكون نصًا غير فارغ.")
        count = interpreter.require_integer(node, amount, "عرض الخط")
        if count < 0:
            interpreter.error(node, "عرض الخط يجب أن يكون غير سالب.")
        return character * count

    interpreter.globals.define("ألوان", {name: name for name in COLORS})
    interpreter._builtin("لوّن", 2, 2, color)
    interpreter._builtin("امسح", 0, 0, clear)
    interpreter._builtin("انتظر", 1, 1, wait)
    interpreter._builtin("عرض_الطرفية", 0, 0, width)
    interpreter._builtin("ارتفاع_الطرفية", 0, 0, height)
    interpreter._builtin("حجم_الطرفية", 0, 0, dimensions)
    interpreter._builtin("كرر", 2, 2, repeat)
    interpreter._builtin("اكتب", 1, 2, write)
    interpreter._builtin("نص_يمين", 1, 1, right_text)
    interpreter._builtin("اطبع_يمين", 1, 2, print_right)
    interpreter._builtin("أدخل_يمين", 0, 1, input_right)
    interpreter._builtin("اخرج", 0, 1, exit_program)
    interpreter._builtin("خط", 0, 2, line)
    for color_name in COLORS:
        interpreter._builtin(color_name, 1, 1, lambda args, _i, node, name=color_name: _color(interpreter, args[0], name, node))
