"""امتدادات المكتبة المعيارية للغة نُطْق.

توفر عمليات ملفات وJSON وSQLite مع إبقاء المسارات داخل مجلد المشروع.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path
import sqlite3
from typing import Any

from .core import Call, CallableValue, Interpreter, NativeFunction, Node, PropertyAccessible, Token


def _project_path(interpreter: Interpreter, value: Any, node: Node) -> Path:
    if not isinstance(value, str) or not value:
        interpreter.error(node, "المسار يجب أن يكون نصًا غير فارغ.")
    try:
        candidate = (interpreter.project_dir / value).resolve()
        if candidate != interpreter.project_dir and interpreter.project_dir not in candidate.parents:
            raise ValueError
        return candidate
    except (OSError, ValueError):
        interpreter.error(node, "المسار يجب أن يبقى داخل مجلد المشروع.")
    raise AssertionError("غير قابل للوصول")


class DatabaseValue(PropertyAccessible):
    """اتصال SQLite يقدّم طريقتي «نفذ» و«أغلق» داخل لغة نُطْق."""

    def __init__(self, path: Path):
        self.path = path
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.closed = False

    def get_property(self, interpreter: Interpreter, name: Token, node: Node) -> Any:
        if name.value == "نفذ":
            return NativeFunction("قاعدة.نفذ", 1, 2, self._execute)
        if name.value == "أغلق":
            return NativeFunction("قاعدة.أغلق", 0, 0, self._close)
        interpreter.error(node, f"اتصال قاعدة البيانات لا يملك الخاصية «{name.value}».")

    def _ensure_open(self, interpreter: Interpreter, node: Call) -> None:
        if self.closed:
            interpreter.error(node, "اتصال قاعدة البيانات مغلق.")

    def _execute(self, args: list[Any], interpreter: Interpreter, node: Call) -> Any:
        self._ensure_open(interpreter, node)
        sql = args[0]
        if not isinstance(sql, str) or not sql.strip():
            interpreter.error(node, "الوسيط الأول لـ«نفذ» يجب أن يكون نص SQL غير فارغ.")
        parameters: list[Any] = []
        if len(args) == 2:
            if not isinstance(args[1], list):
                interpreter.error(node, "المعاملات في «نفذ» يجب أن تكون قائمة أو اتركها فارغة.")
            parameters = args[1]
        try:
            cursor = self.connection.execute(sql, parameters)
            if cursor.description is not None:
                return [dict(row) for row in cursor.fetchall()]
            self.connection.commit()
            return {"صفوف": cursor.rowcount, "معرف_أخير": cursor.lastrowid}
        except sqlite3.Error as error:
            interpreter.error(node, f"خطأ SQLite: {error}")
        raise AssertionError("غير قابل للوصول")

    def _close(self, _args: list[Any], interpreter: Interpreter, node: Call) -> None:
        self._ensure_open(interpreter, node)
        self.connection.close()
        self.closed = True
        return None

    def __str__(self) -> str:
        return f"<قاعدة {self.path.name}>"


def install_standard_extensions(interpreter: Interpreter) -> None:
    """يسجل دوال البيانات والملفات في بيئة مفسر واحد."""

    def to_json(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        try:
            return json.dumps(args[0], ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            interpreter.error(node, "القيمة لا يمكن تحويلها إلى JSON؛ استخدم بيانات بسيطة وقوائم وقواميس.")
        raise AssertionError("غير قابل للوصول")

    def from_json(args: list[Any], _interpreter: Interpreter, node: Call) -> Any:
        if not isinstance(args[0], str):
            interpreter.error(node, "الدالة «من_JSON» تتطلب نصًا.")
        try:
            return json.loads(args[0])
        except json.JSONDecodeError as error:
            interpreter.error(node, f"JSON غير صالح: {error.msg}.")
        raise AssertionError("غير قابل للوصول")

    def read_file(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        path = _project_path(interpreter, args[0], node)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            interpreter.error(node, f"الملف «{args[0]}» غير موجود.")
        except OSError as error:
            interpreter.error(node, f"تعذر قراءة الملف: {error}")
        raise AssertionError("غير قابل للوصول")

    def write_file(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        path = _project_path(interpreter, args[0], node)
        content = args[1]
        if not isinstance(content, str):
            content = interpreter.format_value(content)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as error:
            interpreter.error(node, f"تعذر كتابة الملف: {error}")
        return None

    def exists(args: list[Any], _interpreter: Interpreter, node: Call) -> bool:
        return _project_path(interpreter, args[0], node).exists()

    def open_database(args: list[Any], _interpreter: Interpreter, node: Call) -> DatabaseValue:
        path = _project_path(interpreter, args[0], node)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            return DatabaseValue(path)
        except (OSError, sqlite3.Error) as error:
            interpreter.error(node, f"تعذر فتح قاعدة البيانات: {error}")
        raise AssertionError("غير قابل للوصول")

    def sort_list(args: list[Any], _interpreter: Interpreter, node: Call) -> list[Any]:
        if not isinstance(args[0], list):
            interpreter.error(node, "الدالة «رتب» تتطلب قائمة.")
        try:
            return sorted(args[0])
        except TypeError:
            interpreter.error(node, "لا يمكن ترتيب قائمة تحتوي أنواعًا غير قابلة للمقارنة.")
        raise AssertionError("غير قابل للوصول")

    def reverse_list(args: list[Any], _interpreter: Interpreter, node: Call) -> list[Any]:
        if not isinstance(args[0], list):
            interpreter.error(node, "الدالة «اعكس» تتطلب قائمة.")
        return list(reversed(args[0]))

    def escape_html(args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        return escape(interpreter.format_value(args[0]), quote=True)

    def join_list(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        if not isinstance(args[0], list):
            interpreter.error(node, "الدالة «انضم» تتطلب قائمة.")
        separator = args[1] if len(args) == 2 else ""
        if not isinstance(separator, str):
            interpreter.error(node, "فاصل «انضم» يجب أن يكون نصًا.")
        return separator.join(interpreter.format_value(item) for item in args[0])

    interpreter._builtin("إلى_JSON", 1, 1, to_json)
    interpreter._builtin("من_JSON", 1, 1, from_json)
    interpreter._builtin("اقرأ_ملف", 1, 1, read_file)
    interpreter._builtin("اكتب_ملف", 2, 2, write_file)
    interpreter._builtin("يوجد", 1, 1, exists)
    interpreter._builtin("افتح_قاعدة", 1, 1, open_database)
    interpreter._builtin("رتب", 1, 1, sort_list)
    interpreter._builtin("اعكس", 1, 1, reverse_list)
    interpreter._builtin("هروب_HTML", 1, 1, escape_html)
    interpreter._builtin("انضم", 1, 2, join_list)
