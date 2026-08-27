"""اختبارات تكامل طبقة الويب في لغة نُطْق."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from http.server import ThreadingHTTPServer

from nutaq import Interpreter, parse


SOURCE = """
دالة الرئيسية(طلب) {
    أرجع صفحة(قالب("الرئيسية.html"، {"اسم": طلب["استعلام"]["اسم"]}))
}

دالة منتج(طلب) {
    دع معرف = عدد(طلب["معاملات"]["معرف"])
    أرجع JSON({"معرف": معرف، "اسم": "منتج نُطْق"})
}

دالة تواصل(طلب) {
    إذا طلب["بيانات"] == عدم {
        أرجع JSON({"خطأ": "بيانات مطلوبة"}، 400)
    }
    أرجع JSON({"تم": صحيح، "رسالة": طلب["بيانات"]["رسالة"]}، 201)
}

دالة تعديل_مورد(طلب) {
    أرجع JSON({"طريقة": طلب["طريقة"]، "معرف": عدد(طلب["معاملات"]["معرف"])})
}

ثابت("/static")
مسار("GET"، "/"، الرئيسية)
مسار("GET"، "/api/منتج/{معرف}"، منتج)
مسار("POST"، "/api/تواصل"، تواصل)
مسار("PATCH"، "/api/مورد/{معرف}"، تعديل_مورد)
مسار("DELETE"، "/api/مورد/{معرف}"، تعديل_مورد)
"""


class TestWebPlatform(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        project = Path(self.temporary.name)
        (project / "قوالب").mkdir()
        (project / "static").mkdir()
        (project / "قوالب" / "الرئيسية.html").write_text("<h1>مرحبًا {{اسم}}</h1>", encoding="utf-8")
        (project / "static" / "style.css").write_text("body { color: #123; }", encoding="utf-8")

        self.interpreter = Interpreter(project_dir=project)
        self.interpreter.interpret(parse(SOURCE))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.interpreter.web_app._handler_class())
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def fetch(self, path: str, method: str = "GET", data: bytes | None = None, headers: dict[str, str] | None = None):
        # يرسل HTTP المسارات العربية بترميز percent-encoding كما يفعل المتصفح.
        url = self.base + quote(path, safe="/?=&%")
        request = Request(url, data=data, method=method, headers=headers or {})
        return urlopen(request, timeout=2)

    def test_template_escapes_query_value(self) -> None:
        escaped_name = quote("<script>غير_آمن</script>")
        with self.fetch("/?اسم=" + escaped_name) as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("&lt;script&gt;غير_آمن&lt;/script&gt;", body)
            self.assertNotIn("<script>غير_آمن</script>", body)

    def test_dynamic_route_returns_arabic_json(self) -> None:
        with self.fetch("/api/منتج/7") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "application/json; charset=utf-8")
            self.assertEqual(json.loads(response.read().decode("utf-8")), {"معرف": 7, "اسم": "منتج نُطْق"})

    def test_post_json_body_and_status(self) -> None:
        data = json.dumps({"رسالة": "مرحبًا من المتصفح"}, ensure_ascii=False).encode("utf-8")
        with self.fetch("/api/تواصل", "POST", data, {"Content-Type": "application/json"}) as response:
            self.assertEqual(response.status, 201)
            self.assertEqual(json.loads(response.read().decode("utf-8")), {"تم": True, "رسالة": "مرحبًا من المتصفح"})

    def test_patch_and_delete_dynamic_routes(self) -> None:
        for method in ("PATCH", "DELETE"):
            with self.fetch("/api/مورد/12", method) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read().decode("utf-8")), {"طريقة": method, "معرف": 12})

    def test_static_file_is_served(self) -> None:
        with self.fetch("/static/style.css") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/css", response.headers["Content-Type"])
            self.assertIn("color", response.read().decode("utf-8"))

    def test_unknown_route_is_404(self) -> None:
        with self.assertRaises(HTTPError) as context:
            self.fetch("/غير-موجود")
        self.assertEqual(context.exception.code, 404)
        self.assertIn("غير موجودة", context.exception.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
