"""اختبارات مكتبة الطرفية العربية في نُطْق."""
from __future__ import annotations

from unittest.mock import patch
import unittest

from nutaq import run


class TestNutaqTerminal(unittest.TestCase):
    def execute(self, source: str, **kwargs) -> list[str]:
        output: list[str] = []
        run(source, output.append, **kwargs)
        return output

    def test_named_colors_and_color_dictionary(self) -> None:
        output = self.execute('اطبع(أحمر("خطر"))\nاطبع(لوّن("نجاح"، ألوان.أخضر))')
        self.assertEqual(output[0], "\033[91mخطر\033[0m")
        self.assertEqual(output[1], "\033[92mنجاح\033[0m")

    def test_raw_write_and_clear(self) -> None:
        raw: list[str] = []
        run('اكتب("مرحبًا"، "\\r")\nامسح()', raw_output=raw.append, terminal_rtl=True)
        self.assertEqual(raw[0], "\u2067مرحبًا\u2069")
        self.assertEqual(raw[1], "\r")
        self.assertEqual(raw[2], "\033[2J\033[H")

    def test_right_input_and_output_direction_markers(self) -> None:
        prompts: list[str] = []
        output: list[str] = []
        run(
            'دع اسم = أدخل_يمين("اكتب اسمك: ")\nاطبع_يمين("مرحبًا " + اسم، "أزرق")',
            output.append,
            input_provider=lambda prompt: prompts.append(prompt) or "سارة",
            terminal_rtl=True,
        )
        self.assertEqual(prompts, ["\u2067اكتب اسمك: \u2069"])
        self.assertTrue(output[0].startswith("\u2067"))
        self.assertTrue(output[0].endswith("\u2069"))
        self.assertIn("\033[94m", output[0])

    def test_wait_repeat_dimensions_and_line(self) -> None:
        with patch("nutaq.terminal.time.sleep") as sleep:
            output = self.execute('انتظر(1.5)\nاطبع(كرر("*"، 3))\nاطبع(طول(خط("-"، 5)))')
        sleep.assert_called_once_with(1.5)
        self.assertEqual(output, ["***", "5"])

    def test_exit_has_requested_status(self) -> None:
        with self.assertRaises(SystemExit) as context:
            run("اخرج(7)")
        self.assertEqual(context.exception.code, 7)


if __name__ == "__main__":
    unittest.main()
