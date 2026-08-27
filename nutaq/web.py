"""طبقة الويب العربية المدمجة للغة نُطْق.

تظل واجهة هذه الوحدة مخفية خلف دوال عربية مسجلة في بيئة اللغة.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from threading import RLock
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlsplit

from .core import Call, CallableValue, Interpreter, Literal, NutaqError, Token


@dataclass
class WebResponse:
    """تمثيل استجابة HTTP لا يظهر إلا بوصفه قيمة تُعيدها دوال نُطْق."""

    body: str | bytes
    status: int = 200
    content_type: str = "text/html; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Route:
    method: str
    pattern: str
    handler: CallableValue
    regex: re.Pattern[str]
    parameter_names: list[str]


@dataclass
class StaticMount:
    prefix: str
    directory: Path


class WebApp:
    """مسجّل مسارات ومشغّل HTTP لتطبيق نُطْق واحد."""

    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        self.routes: list[Route] = []
        self.static_mounts: list[StaticMount] = []
        self.lock = RLock()
        self.server: Optional[ThreadingHTTPServer] = None

    def add_route(self, method: str, pattern: str, handler: CallableValue, node: Call) -> None:
        method = method.upper().strip()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
            self.interpreter.error(node, "طريقة المسار يجب أن تكون إحدى GET أو POST أو PUT أو PATCH أو DELETE أو HEAD أو OPTIONS.")
        if not pattern.startswith("/"):
            self.interpreter.error(node, "نمط المسار يجب أن يبدأ بالرمز /.")
        if not isinstance(handler, CallableValue):
            self.interpreter.error(node, "الوسيط الثالث لـ«مسار» يجب أن يكون دالة.")
        regex, names = self._compile_route(pattern, node)
        if any(route.method == method and route.pattern == pattern for route in self.routes):
            self.interpreter.error(node, f"المسار «{method} {pattern}» مسجّل بالفعل.")
        self.routes.append(Route(method, pattern, handler, regex, names))

    def add_static(self, prefix: str, directory: str, node: Call) -> None:
        if not prefix.startswith("/"):
            self.interpreter.error(node, "بادئة الملفات الثابتة يجب أن تبدأ بالرمز /.")
        normalized = prefix.rstrip("/") or "/"
        root = self._safe_project_path(directory, node, "مجلد الملفات الثابتة")
        self.static_mounts.append(StaticMount(normalized, root))

    def template(self, name: str, context: Any, node: Call) -> str:
        if not isinstance(name, str):
            self.interpreter.error(node, "اسم القالب يجب أن يكون نصًا.")
        if context is None:
            context = {}
        if not isinstance(context, dict):
            self.interpreter.error(node, "سياق القالب يجب أن يكون قاموسًا أو عدم.")
        template_root = (self.interpreter.project_dir / "قوالب").resolve()
        try:
            candidate = self._resolve_inside(template_root, name)
            source = candidate.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.interpreter.error(node, f"القالب «{name}» غير موجود داخل مجلد قوالب.")
        except (OSError, ValueError):
            self.interpreter.error(node, f"مسار القالب «{name}» غير آمن أو غير قابل للقراءة.")
        return self._render_template(source, context)

    def serve(self, port: int, host: str, node: Call) -> None:
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            self.interpreter.error(node, "منفذ الخادم يجب أن يكون عددًا صحيحًا بين 1 و65535.")
        if not isinstance(host, str) or not host:
            self.interpreter.error(node, "مضيف الخادم يجب أن يكون نصًا غير فارغ.")
        if self.server is not None:
            self.interpreter.error(node, "الخادم يعمل بالفعل لهذا التطبيق.")
        handler_class = self._handler_class()
        try:
            self.server = ThreadingHTTPServer((host, port), handler_class)
        except OSError as error:
            self.interpreter.error(node, f"تعذر بدء الخادم على {host}:{port}: {error}")
        self.interpreter.output(f"خادم نُطْق يعمل على http://{host}:{port}")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.interpreter.output("\nتم إيقاف خادم نُطْق.")
        finally:
            self.server.server_close()
            self.server = None

    def dispatch(self, request_handler: BaseHTTPRequestHandler) -> None:
        """يعالج طلبًا واحدًا وينشئ استجابة HTTP؛ تستخدمه الفئة الداخلية فقط."""
        split = urlsplit(request_handler.path)
        path = unquote(split.path) or "/"
        method = request_handler.command.upper()
        route, parameters = self._match_route(method, path)
        if route is not None:
            request = self._request_value(request_handler, path, parameters, split.query)
            node = self._internal_call_node()
            try:
                # بيئة المفسّر مشتركة، ولذلك تنفذ طلبات تطبيق واحد بالتتابع بأمان.
                with self.lock:
                    result = route.handler.call(self.interpreter, [request], node)
                response = self._coerce_response(result, node)
            except NutaqError as error:
                response = self._error_response(500, f"خطأ داخل التطبيق: {error.message}")
            except Exception:
                response = self._error_response(500, "حدث خطأ داخلي غير متوقع في التطبيق.")
            self._send(request_handler, response, include_body=method != "HEAD")
            return

        if method in {"GET", "HEAD"}:
            static_response = self._static_response(path)
            if static_response is not None:
                self._send(request_handler, static_response, include_body=method != "HEAD")
                return
        self._send(request_handler, self._error_response(404, "الصفحة المطلوبة غير موجودة."), include_body=method != "HEAD")

    def _compile_route(self, pattern: str, node: Call) -> tuple[re.Pattern[str], list[str]]:
        if pattern == "/":
            return re.compile(r"^/$"), []
        parts = pattern.strip("/").split("/")
        names: list[str] = []
        regex_parts: list[str] = []
        for part in parts:
            matched = re.fullmatch(r"\{([^/{}]+)\}", part)
            if matched:
                name = matched.group(1)
                if name in names:
                    self.interpreter.error(node, f"اسم معامل المسار «{name}» مكرر.")
                names.append(name)
                regex_parts.append(r"([^/]+)")
            elif "{" in part or "}" in part:
                self.interpreter.error(node, "يجب أن يشغل معامل المسار جزءًا كاملًا، مثل /مقال/{معرف}.")
            else:
                regex_parts.append(re.escape(part))
        return re.compile("^/" + "/".join(regex_parts) + r"/?$"), names

    def _match_route(self, method: str, path: str) -> tuple[Optional[Route], dict[str, str]]:
        for route in self.routes:
            if route.method != method:
                continue
            matched = route.regex.match(path)
            if matched:
                return route, dict(zip(route.parameter_names, [unquote(value) for value in matched.groups()]))
        return None, {}

    def _request_value(self, handler: BaseHTTPRequestHandler, path: str, parameters: dict[str, str], query: str) -> dict[str, Any]:
        length_text = handler.headers.get("Content-Length", "0")
        try:
            length = max(0, int(length_text))
        except ValueError:
            length = 0
        raw = handler.rfile.read(length) if length else b""
        text = raw.decode("utf-8", errors="replace")
        content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        data: Any = None
        if text and content_type == "application/json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
        elif text and content_type == "application/x-www-form-urlencoded":
            data = self._first_values(parse_qs(text, keep_blank_values=True))
        return {
            "طريقة": handler.command.upper(),
            "مسار": path,
            "معاملات": parameters,
            "استعلام": self._first_values(parse_qs(query, keep_blank_values=True)),
            "رؤوس": {name: value for name, value in handler.headers.items()},
            "نص": text,
            "بيانات": data,
        }

    @staticmethod
    def _first_values(values: dict[str, list[str]]) -> dict[str, str]:
        return {key: value[0] if value else "" for key, value in values.items()}

    def _coerce_response(self, result: Any, node: Call) -> WebResponse:
        if isinstance(result, WebResponse):
            return result
        if isinstance(result, str):
            return WebResponse(result)
        if isinstance(result, (dict, list)):
            return self.json_response(result, 200, node)
        if result is None:
            return self._error_response(500, "لم تُعد دالة المسار استجابة.")
        return WebResponse(self.interpreter.format_value(result))

    def page_response(self, content: Any, status: Any, headers: Any, node: Call) -> WebResponse:
        return WebResponse(
            self.interpreter.format_value(content),
            self._status(status, node),
            "text/html; charset=utf-8",
            self._headers(headers, node),
        )

    def text_response(self, content: Any, status: Any, headers: Any, node: Call) -> WebResponse:
        return WebResponse(
            self.interpreter.format_value(content),
            self._status(status, node),
            "text/plain; charset=utf-8",
            self._headers(headers, node),
        )

    def json_response(self, value: Any, status: Any, node: Call) -> WebResponse:
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            self.interpreter.error(node, "بيانات JSON يجب أن تتألف من أعداد ونصوص ومنطقيات وقوائم وقواميس فقط.")
        return WebResponse(encoded, self._status(status, node), "application/json; charset=utf-8")

    def redirect_response(self, location: Any, status: Any, node: Call) -> WebResponse:
        if not isinstance(location, str) or not location:
            self.interpreter.error(node, "وجهة إعادة التوجيه يجب أن تكون نصًا غير فارغ.")
        return WebResponse("", self._status(status, node), "text/plain; charset=utf-8", {"Location": location})

    def _status(self, value: Any, node: Call) -> int:
        if value is None:
            return 200
        if not isinstance(value, int) or isinstance(value, bool) or not 100 <= value <= 599:
            self.interpreter.error(node, "حالة HTTP يجب أن تكون عددًا صحيحًا بين 100 و599.")
        return value

    def _headers(self, value: Any, node: Call) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            self.interpreter.error(node, "رؤوس الاستجابة يجب أن تكون قاموسًا أو عدم.")
        headers: dict[str, str] = {}
        for name, header_value in value.items():
            if not isinstance(name, str):
                self.interpreter.error(node, "اسم رأس الاستجابة يجب أن يكون نصًا.")
            if "\r" in name or "\n" in name:
                self.interpreter.error(node, "اسم رأس الاستجابة غير صالح.")
            text = self.interpreter.format_value(header_value)
            if "\r" in text or "\n" in text:
                self.interpreter.error(node, "قيمة رأس الاستجابة غير صالحة.")
            headers[name] = text
        return headers

    def _safe_project_path(self, value: str, node: Call, description: str) -> Path:
        if not isinstance(value, str) or not value:
            self.interpreter.error(node, f"{description} يجب أن يكون نصًا غير فارغ.")
        try:
            return self._resolve_inside(self.interpreter.project_dir, value)
        except ValueError:
            self.interpreter.error(node, f"{description} يجب أن يبقى داخل مجلد المشروع.")
        raise AssertionError("غير قابل للوصول")

    @staticmethod
    def _resolve_inside(root: Path, relative: str) -> Path:
        root = root.resolve()
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError("مسار خارج الجذر")
        return candidate

    def _render_template(self, source: str, context: dict[str, Any]) -> str:
        def lookup(expression: str) -> Any:
            value: Any = context
            for part in expression.strip().split("."):
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    return ""
            return value

        def raw_replacement(match: re.Match[str]) -> str:
            return self.interpreter.format_value(lookup(match.group(1)))

        def escaped_replacement(match: re.Match[str]) -> str:
            return escape(self.interpreter.format_value(lookup(match.group(1))), quote=True)

        source = re.sub(r"\{\{\{\s*([^{}]+?)\s*\}\}\}", raw_replacement, source)
        return re.sub(r"\{\{\s*([^{}]+?)\s*\}\}", escaped_replacement, source)

    def _static_response(self, path: str) -> Optional[WebResponse]:
        for mount in self.static_mounts:
            prefix = mount.prefix
            if path == prefix:
                relative = ""
            elif prefix != "/" and path.startswith(prefix + "/"):
                relative = path[len(prefix) + 1:]
            elif prefix == "/":
                relative = path.lstrip("/")
            else:
                continue
            try:
                candidate = self._resolve_inside(mount.directory, relative)
            except ValueError:
                return self._error_response(403, "مسار الملف غير مسموح به.")
            if not candidate.is_file():
                return None
            try:
                content = candidate.read_bytes()
            except OSError:
                return self._error_response(404, "تعذر قراءة الملف الثابت.")
            content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in {"application/javascript", "application/json", "image/svg+xml"}:
                content_type += "; charset=utf-8"
            return WebResponse(content, 200, content_type)
        return None

    @staticmethod
    def _error_response(status: int, message: str) -> WebResponse:
        safe = escape(message)
        document = f"<!doctype html><html lang=\"ar\" dir=\"rtl\"><meta charset=\"utf-8\"><title>خطأ {status}</title><body><h1>خطأ {status}</h1><p>{safe}</p></body></html>"
        return WebResponse(document, status)

    @staticmethod
    def _internal_call_node() -> Call:
        token = Token("PUNCT", "(", 1, 1)
        return Call(1, 1, Literal(1, 1, None), token, [])

    @staticmethod
    def _send(handler: BaseHTTPRequestHandler, response: WebResponse, include_body: bool = True) -> None:
        payload = response.body.encode("utf-8") if isinstance(response.body, str) else response.body
        headers = {"Content-Type": response.content_type, "X-Content-Type-Options": "nosniff", **response.headers}
        handler.send_response(response.status)
        for name, value in headers.items():
            handler.send_header(name, value)
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        if include_body:
            handler.wfile.write(payload)

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        application = self

        class NutaqRequestHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_POST(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_PUT(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_PATCH(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_DELETE(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_HEAD(self) -> None:  # noqa: N802
                application.dispatch(self)

            def do_OPTIONS(self) -> None:  # noqa: N802
                application.dispatch(self)

            def log_message(self, _format: str, *_args: Any) -> None:
                # يمنع سجل HTTP الافتراضي من تشويش مخرجات التطبيق.
                return

        return NutaqRequestHandler


def install_web_builtins(interpreter: Interpreter) -> None:
    """يسجّل دوال الويب العربية داخل بيئة مفسّر واحد."""
    app = WebApp(interpreter)
    interpreter.web_app = app

    def route(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        method, pattern, handler = args
        if not isinstance(method, str) or not isinstance(pattern, str):
            interpreter.error(node, "الوسيطان الأول والثاني لـ«مسار» يجب أن يكونا نصين.")
        app.add_route(method, pattern, handler, node)
        return None

    def page(args: list[Any], _interpreter: Interpreter, node: Call) -> WebResponse:
        status = args[1] if len(args) >= 2 else 200
        headers = args[2] if len(args) >= 3 else None
        return app.page_response(args[0], status, headers, node)

    def text(args: list[Any], _interpreter: Interpreter, node: Call) -> WebResponse:
        status = args[1] if len(args) >= 2 else 200
        headers = args[2] if len(args) >= 3 else None
        return app.text_response(args[0], status, headers, node)

    def json_value(args: list[Any], _interpreter: Interpreter, node: Call) -> WebResponse:
        status = args[1] if len(args) >= 2 else 200
        return app.json_response(args[0], status, node)

    def redirect(args: list[Any], _interpreter: Interpreter, node: Call) -> WebResponse:
        status = args[1] if len(args) >= 2 else 302
        return app.redirect_response(args[0], status, node)

    def template(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        context = args[1] if len(args) >= 2 else None
        return app.template(args[0], context, node)

    def static(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        directory = args[1] if len(args) >= 2 else "static"
        if not isinstance(args[0], str) or not isinstance(directory, str):
            interpreter.error(node, "بادئة ومجلد الملفات الثابتة يجب أن يكونا نصين.")
        app.add_static(args[0], directory, node)
        return None

    def serve(args: list[Any], _interpreter: Interpreter, node: Call) -> None:
        port = args[0] if args else 8000
        host = args[1] if len(args) >= 2 else "127.0.0.1"
        app.serve(port, host, node)
        return None

    interpreter._builtin("مسار", 3, 3, route)
    interpreter._builtin("صفحة", 1, 3, page)
    interpreter._builtin("استجابة_نص", 1, 3, text)
    interpreter._builtin("JSON", 1, 2, json_value)
    interpreter._builtin("إعادة_توجيه", 1, 2, redirect)
    interpreter._builtin("قالب", 1, 2, template)
    interpreter._builtin("ثابت", 1, 2, static)
    interpreter._builtin("شغّل", 0, 2, serve)
