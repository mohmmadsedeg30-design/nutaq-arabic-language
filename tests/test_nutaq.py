"""اختبارات الانحدار لنواة لغة نُطْق."""
from __future__ import annotations

import unittest

from nutaq import NutaqError, run


def execute(source: str) -> list[str]:
    output: list[str] = []
    run(source, output.append)
    return output


class TestNutaqLanguage(unittest.TestCase):
    def test_arithmetic_precedence_and_arabic_digits(self) -> None:
        self.assertEqual(execute("دع نتيجة = ٢ + ٣ * ٤\nاطبع(نتيجة)"), ["14"])
        self.assertEqual(execute("اطبع(٣٫٥ + ١)"), ["4.5"])

    def test_strings_lists_and_index_assignment(self) -> None:
        source = """
دع عناصر = ["أ", "ب"، "ج"]
عناصر[1] = "ت"
اطبع(عناصر[1])
اطبع("مر" + "حبًا")
"""
        self.assertEqual(execute(source), ["ت", "مرحبًا"])

    def test_dictionary_and_standard_library(self) -> None:
        source = """
دع درجات = {"سارة": 98، "ليان": 91}
أضف(قيم(درجات)، 77)
اطبع(طول(مفاتيح(درجات)))
اطبع(درجات["سارة"])
"""
        self.assertEqual(execute(source), ["2", "98"])

    def test_for_loop_updates_enclosing_scope(self) -> None:
        source = """
دع مجموع = 0
لكل قيمة في [2، 3، 5] {
    مجموع = مجموع + قيمة
}
اطبع(مجموع)
"""
        self.assertEqual(execute(source), ["10"])

    def test_while_break_and_continue(self) -> None:
        source = """
دع ن = 0
دع مجموع = 0
بينما ن < 6 {
    ن = ن + 1
    إذا ن == 3 { تابع }
    إذا ن == 5 { توقف }
    مجموع = مجموع + ن
}
اطبع(مجموع)
"""
        self.assertEqual(execute(source), ["7"])

    def test_function_recursion(self) -> None:
        source = """
دالة عاملي(ن) {
    إذا ن <= 1 { أرجع 1 }
    أرجع ن * عاملي(ن - 1)
}
اطبع(عاملي(6))
"""
        self.assertEqual(execute(source), ["720"])

    def test_function_closure_and_outer_assignment(self) -> None:
        source = """
دع أساس = 10
دع عداد = 0
دالة أضف_للأساس(قيمة) {
    عداد = عداد + 1
    أرجع أساس + قيمة
}
اطبع(أضف_للأساس(5))
اطبع(عداد)
"""
        self.assertEqual(execute(source), ["15", "1"])

    def test_logical_operators_are_short_circuiting(self) -> None:
        source = """
اطبع(خطأ و اسم_غير_معرف)
اطبع(صحيح أو اسم_غير_معرف)
اطبع(ليس خطأ)
"""
        self.assertEqual(execute(source), ["خطأ", "صحيح", "صحيح"])

    def test_range_conversion_and_list_mutation(self) -> None:
        source = """
دع أرقام = نطاق(1، 6، 2)
أضف(أرقام، عدد("٧"))
اطبع(نص(أرقام))
اطبع(احذف(أرقام، 1))
اطبع(نوع(أرقام))
"""
        self.assertEqual(execute(source), ["[1، 3، 5، 7]", "3", "قائمة"])

    def test_nested_else_if(self) -> None:
        source = """
دع درجة = 86
إذا درجة >= 90 { اطبع("ممتاز") }
وإلا إذا درجة >= 80 { اطبع("جيد جدًا") }
وإلا { اطبع("جيد") }
"""
        self.assertEqual(execute(source), ["جيد جدًا"])

    def test_runtime_error_has_arabic_diagnostics(self) -> None:
        with self.assertRaises(NutaqError) as context:
            run("اطبع(مجهول)")
        self.assertEqual(context.exception.kind, "خطأ_اسم")
        self.assertEqual(context.exception.line, 1)
        self.assertIn("مجهول", str(context.exception))

    def test_syntax_error_has_position(self) -> None:
        with self.assertRaises(NutaqError) as context:
            run("دع = 3")
        self.assertEqual(context.exception.kind, "خطأ_نحوي")
        self.assertEqual(context.exception.line, 1)

    def test_illegal_control_statement_is_reported(self) -> None:
        with self.assertRaises(NutaqError) as context:
            run("توقف")
        self.assertEqual(context.exception.kind, "خطأ_تنفيذي")
        self.assertIn("خارج حلقة", str(context.exception))


if __name__ == "__main__":
    unittest.main()
