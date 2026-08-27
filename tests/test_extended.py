"""اختبارات الميزات الموسعة في نُطْق 0.3."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from nutaq import NutaqError, run


class TestExtendedLanguage(unittest.TestCase):
    def execute(self, source: str, project_dir: str | Path | None = None) -> list[str]:
        output: list[str] = []
        run(source, output.append, project_dir=project_dir)
        return output

    def test_class_properties_and_methods(self) -> None:
        source = """
صنف عداد {
    دالة تهيئة(ذات، بداية) {
        ذات.قيمة = بداية
    }
    دالة زد(ذات، مقدار) {
        ذات.قيمة = ذات.قيمة + مقدار
        أرجع ذات.قيمة
    }
}
دع عدادي = عداد(4)
اطبع(عدادي.زد(3))
اطبع(عدادي.قيمة)
اطبع(نوع(عدادي))
"""
        self.assertEqual(self.execute(source), ["7", "7", "كائن"])

    def test_try_catch_finally_with_thrown_value(self) -> None:
        source = """
حاول {
    ارم "لم يكتمل الطلب"
} التقط مشكلة {
    اطبع(مشكلة.نوع)
    اطبع(مشكلة.رسالة)
} أخيرًا {
    اطبع("تنظيف")
}
"""
        self.assertEqual(self.execute(source), ["خطأ_مرمي", "لم يكتمل الطلب", "تنظيف"])

    def test_try_catches_runtime_errors(self) -> None:
        source = """
حاول {
    اطبع(اسم_مجهول)
} التقط خطأ {
    اطبع(خطأ.نوع)
    اطبع(خطأ.سطر)
}
"""
        self.assertEqual(self.execute(source), ["خطأ_اسم", "3"])

    def test_import_local_module_once_and_access_property(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "مكتبات").mkdir()
            (project / "مكتبات" / "حساب.نطق").write_text(
                "دع اسم = \"الحساب\"\nدالة ضعف(ن) { أرجع ن * 2 }\n", encoding="utf-8"
            )
            source = """
استورد "مكتبات/حساب.نطق" ك حساب
اطبع(حساب.اسم)
اطبع(حساب.ضعف(9))
"""
            self.assertEqual(self.execute(source, project), ["الحساب", "18"])

    def test_json_and_project_scoped_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = """
دع محتوى = إلى_JSON({"الاسم": "نُطْق"، "إصدار": 3})
اكتب_ملف("بيانات/إعدادات.json"، محتوى)
دع بيانات = من_JSON(اقرأ_ملف("بيانات/إعدادات.json"))
اطبع(بيانات.الاسم)
اطبع(بيانات.إصدار)
اطبع(يوجد("بيانات/إعدادات.json"))
"""
            self.assertEqual(self.execute(source, temporary), ["نُطْق", "3", "صحيح"])

    def test_project_scoped_files_reject_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(NutaqError) as context:
                self.execute('اقرأ_ملف("../خارج.txt")', temporary)
            self.assertEqual(context.exception.kind, "خطأ_تنفيذي")
            self.assertIn("مجلد المشروع", context.exception.message)

    def test_sqlite_parameterized_crud(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = """
دع قاعدة = افتح_قاعدة("بيانات/مهام.db")
قاعدة.نفذ("CREATE TABLE IF NOT EXISTS مهام (معرف INTEGER PRIMARY KEY, عنوان TEXT, مكتملة INTEGER)")
قاعدة.نفذ("INSERT INTO مهام (عنوان, مكتملة) VALUES (?, ?)", ["تعلم نُطْق"، 0])
قاعدة.نفذ("UPDATE مهام SET مكتملة = ? WHERE عنوان = ?", [1، "تعلم نُطْق"])
دع صفوف = قاعدة.نفذ("SELECT عنوان, مكتملة FROM مهام WHERE عنوان = ?", ["تعلم نُطْق"])
اطبع(صفوف[0].عنوان)
اطبع(صفوف[0].مكتملة)
قاعدة.أغلق()
"""
            self.assertEqual(self.execute(source, temporary), ["تعلم نُطْق", "1"])

    def test_html_escaping(self) -> None:
        self.assertEqual(self.execute('اطبع(هروب_HTML("<img src=\\\"x\\\">"))'), ["&lt;img src=&quot;x&quot;&gt;"])

    def test_collection_extensions(self) -> None:
        source = """
دع أرقام = [4، 1، 3]
اطبع(نص(رتب(أرقام)))
اطبع(نص(اعكس(أرقام)))
اطبع(انضم(["أ"، "ب"، "ج"]، "-"))
"""
        self.assertEqual(self.execute(source), ["[1، 3، 4]", "[3، 1، 4]", "أ-ب-ج"])


if __name__ == "__main__":
    unittest.main()
