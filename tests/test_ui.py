"""اختبارات مكتبة واجهات نُطْق الخفيفة."""
from __future__ import annotations

import unittest

from nutaq import NutaqError, run


class TestNutaqUI(unittest.TestCase):
    def execute(self, source: str) -> list[str]:
        output: list[str] = []
        run(source, output.append)
        return output

    def test_assets_and_icon(self) -> None:
        output = self.execute('اطبع(أصول_واجهة())\nاطبع(أيقونة("بحث"، 24))')
        self.assertIn('/_نطق/ui.css', output[0])
        self.assertIn('/_نطق/ui.js', output[0])
        self.assertIn('width="24"', output[1])
        self.assertIn('<circle', output[1])

    def test_components_escape_text_and_preserve_trusted_content(self) -> None:
        source = """
اطبع(زر("<نقر>"، "خطر"))
اطبع(تنبيه("تم الحفظ"، "نجاح"))
اطبع(بطاقة("العنوان"، "<p>محتوى موثوق</p>"))
اطبع(شارة("جديد"، "تحذير"))
"""
        output = self.execute(source)
        self.assertIn("&lt;نقر&gt;", output[0])
        self.assertIn("ن-زر--خطر", output[0])
        self.assertIn("ن-تنبيه--نجاح", output[1])
        self.assertIn("<p>محتوى موثوق</p>", output[2])
        self.assertIn("ن-شارة--تحذير", output[3])

    def test_modal_tabs_and_theme_controls(self) -> None:
        source = """
اطبع(زر_نافذة("تفاصيل"، "عرض التفاصيل"))
اطبع(نافذة("تفاصيل"، "عنوان"، "<p>تفاصيل آمنة</p>"))
اطبع(زر_سمة())
اطبع(تبويبات([{"عنوان": "الأول"، "محتوى": "<p>أ</p>"}، {"عنوان": "الثاني"، "محتوى": "<p>ب</p>"}]))
"""
        output = self.execute(source)
        self.assertIn('data-نطق-نافذة="تفاصيل"', output[0])
        self.assertIn('<dialog', output[1])
        self.assertIn('data-نطق-سمة', output[2])
        self.assertIn('aria-selected="true"', output[3])
        self.assertIn('aria-selected="false"', output[3])

    def test_invalid_icon_is_diagnostic(self) -> None:
        with self.assertRaises(NutaqError) as context:
            run('أيقونة("غير_موجود")')
        self.assertEqual(context.exception.kind, "خطأ_تنفيذي")
        self.assertIn("غير معروف", context.exception.message)


if __name__ == "__main__":
    unittest.main()
