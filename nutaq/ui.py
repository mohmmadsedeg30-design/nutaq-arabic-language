"""مكتبة واجهات عربية خفيفة مدمجة في منصة نُطْق.

تعتمد على CSS وJavaScript صغيرين وأيقونات SVG نصية، ولا تحتاج إلى حزم خارجية.
"""
from __future__ import annotations

from html import escape
import re
from typing import Any

from .core import Call, Interpreter


UI_CSS = r"""
:root{color-scheme:light dark;--ن-أساسي:#2563eb;--ن-أساسي-داكن:#1d4ed8;--ن-ثانوي:#475569;--ن-نجاح:#15803d;--ن-تحذير:#b45309;--ن-خطر:#b91c1c;--ن-خلفية:#f8fafc;--ن-سطح:#fff;--ن-نص:#172033;--ن-نص-هادئ:#5b677a;--ن-حد:#dbe3ee;--ن-ظل:0 8px 24px rgba(15,23,42,.08);--ن-نصف:10px;--ن-مسافة:1rem}
@media(prefers-color-scheme:dark){:root{--ن-خلفية:#0f172a;--ن-سطح:#182235;--ن-نص:#e5eefb;--ن-نص-هادئ:#a8b7cb;--ن-حد:#30415a;--ن-ظل:0 8px 24px rgba(0,0,0,.2)}}
html[data-نطق-سمة="فاتح"]{color-scheme:light;--ن-خلفية:#f8fafc;--ن-سطح:#fff;--ن-نص:#172033;--ن-نص-هادئ:#5b677a;--ن-حد:#dbe3ee}
html[data-نطق-سمة="داكن"]{color-scheme:dark;--ن-خلفية:#0f172a;--ن-سطح:#182235;--ن-نص:#e5eefb;--ن-نص-هادئ:#a8b7cb;--ن-حد:#30415a}
.ن-واجهة{background:var(--ن-خلفية);color:var(--ن-نص);font-family:Tahoma,Arial,sans-serif;line-height:1.7}.ن-واجهة *{box-sizing:border-box}.ن-حاوية{width:min(1100px,calc(100% - 32px));margin:auto}.ن-شبكة{display:grid;gap:var(--ن-مسافة)}.ن-شبكة--2{grid-template-columns:repeat(2,minmax(0,1fr))}.ن-شبكة--3{grid-template-columns:repeat(3,minmax(0,1fr))}
.ن-زر{display:inline-flex;gap:.45rem;align-items:center;justify-content:center;border:1px solid transparent;border-radius:8px;background:var(--ن-أساسي);color:#fff;padding:.6rem .95rem;font:inherit;font-weight:700;cursor:pointer;text-decoration:none;transition:filter .16s,transform .16s}.ن-زر:hover{filter:brightness(.93)}.ن-زر:active{transform:translateY(1px)}.ن-زر--ثانوي{background:transparent;border-color:var(--ن-حد);color:var(--ن-نص)}.ن-زر--خطر{background:var(--ن-خطر)}.ن-زر--نجاح{background:var(--ن-نجاح)}.ن-زر--صغير{font-size:.86rem;padding:.38rem .65rem}
.ن-بطاقة{background:var(--ن-سطح);border:1px solid var(--ن-حد);border-radius:var(--ن-نصف);box-shadow:var(--ن-ظل);overflow:hidden}.ن-بطاقة__رأس,.ن-بطاقة__محتوى,.ن-بطاقة__تذييل{padding:1.05rem 1.2rem}.ن-بطاقة__رأس{border-bottom:1px solid var(--ن-حد)}.ن-بطاقة__عنوان{font-size:1.15rem;margin:0}.ن-بطاقة__تذييل{border-top:1px solid var(--ن-حد);background:color-mix(in srgb,var(--ن-سطح),var(--ن-خلفية) 30%)}
.ن-تنبيه{display:flex;align-items:flex-start;gap:.6rem;border:1px solid var(--ن-حد);border-radius:var(--ن-نصف);padding:.8rem 1rem;margin:.8rem 0}.ن-تنبيه--معلومات{background:#dbeafe;color:#153e75;border-color:#93c5fd}.ن-تنبيه--نجاح{background:#dcfce7;color:#14532d;border-color:#86efac}.ن-تنبيه--تحذير{background:#fef3c7;color:#78350f;border-color:#fcd34d}.ن-تنبيه--خطر{background:#fee2e2;color:#7f1d1d;border-color:#fca5a5}.ن-تنبيه__إغلاق{margin-inline-start:auto;border:0;background:transparent;color:currentColor;font-size:1.15rem;cursor:pointer}
.ن-شارة{display:inline-flex;align-items:center;border-radius:999px;padding:.16rem .58rem;background:#dbeafe;color:#1e40af;font-size:.82rem;font-weight:700}.ن-شارة--نجاح{background:#dcfce7;color:#166534}.ن-شارة--تحذير{background:#fef3c7;color:#92400e}.ن-شارة--خطر{background:#fee2e2;color:#991b1b}.ن-شارة--ثانوي{background:#e2e8f0;color:#334155}.ن-أيقونة{display:inline-block;flex:0 0 auto;vertical-align:-.16em;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.9}
.ن-نافذة{border:0;border-radius:14px;background:var(--ن-سطح);color:var(--ن-نص);padding:0;width:min(560px,calc(100% - 24px));box-shadow:0 25px 70px rgba(0,0,0,.35)}.ن-نافذة::backdrop{background:rgba(15,23,42,.58)}.ن-نافذة__رأس{display:flex;justify-content:space-between;align-items:center;padding:1rem 1.2rem;border-bottom:1px solid var(--ن-حد)}.ن-نافذة__عنوان{margin:0;font-size:1.2rem}.ن-نافذة__إغلاق{border:0;background:transparent;color:var(--ن-نص);cursor:pointer;font-size:1.35rem}.ن-نافذة__محتوى{padding:1.2rem}
.ن-تبويبات{border:1px solid var(--ن-حد);border-radius:var(--ن-نصف);background:var(--ن-سطح)}.ن-تبويبات__قائمة{display:flex;gap:.25rem;overflow:auto;border-bottom:1px solid var(--ن-حد);padding:.45rem}.ن-تبويبات__زر{white-space:nowrap;border:0;border-radius:7px;background:transparent;color:var(--ن-نص-هادئ);padding:.5rem .75rem;font:inherit;font-weight:700;cursor:pointer}.ن-تبويبات__زر[aria-selected="true"]{background:var(--ن-أساسي);color:#fff}.ن-تبويبات__لوح{padding:1rem}.ن-تبويبات__لوح[hidden]{display:none}
@media(max-width:680px){.ن-شبكة--2,.ن-شبكة--3{grid-template-columns:1fr}}
""".strip()

UI_JS = r"""
(()=>{const d=document.documentElement;const key='نطق-سمة';try{const saved=localStorage.getItem(key);if(saved)d.setAttribute('data-نطق-سمة',saved)}catch(_){ }
const applyTheme=()=>{const current=d.getAttribute('data-نطق-سمة')==='داكن'?'فاتح':'داكن';d.setAttribute('data-نطق-سمة',current);try{localStorage.setItem(key,current)}catch(_){ }};
d.addEventListener('click',e=>{const close=e.target.closest('[data-نطق-إغلاق]');if(close){close.closest('.ن-تنبيه')?.remove();return}const theme=e.target.closest('[data-نطق-سمة]');if(theme){applyTheme();return}const opener=e.target.closest('[data-نطق-نافذة]');if(opener){document.getElementById(opener.getAttribute('data-نطق-نافذة'))?.showModal();return}const closer=e.target.closest('[data-نطق-أغلق-نافذة]');if(closer){closer.closest('dialog')?.close();return}const tab=e.target.closest('[data-نطق-تبويب]');if(tab){const root=tab.closest('.ن-تبويبات');root.querySelectorAll('[data-نطق-تبويب]').forEach(x=>x.setAttribute('aria-selected',x===tab?'true':'false'));root.querySelectorAll('[role="tabpanel"]').forEach(x=>x.hidden=x.id!==tab.getAttribute('aria-controls'));}});})();
""".strip()

# مسارات رموز SVG مبسطة من 24×24 كي لا تضيف ملفات أو مكتبات مستقلة.
ICON_PATHS = {
    "منزل": '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1Z"/>',
    "قائمة": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "بحث": '<circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/>',
    "مستخدم": '<circle cx="12" cy="8" r="3.5"/><path d="M4.5 21c.8-4 3.4-6 7.5-6s6.7 2 7.5 6"/>',
    "حذف": '<path d="M4 7h16M10 11v6M14 11v6M9 7l1-3h4l1 3M6 7l1 14h10l1-14"/>',
    "تعديل": '<path d="m4 16.5-.5 4 4-.5L19 8.5 15.5 5ZM13.8 6.7l3.5 3.5"/>',
    "تحقق": '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.6 2.6L16.5 9"/>',
    "شمس": '<circle cx="12" cy="12" r="3.5"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "قمر": '<path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>',
    "سهم": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "اغلاق": '<path d="m6 6 12 12M18 6 6 18"/>',
}

VARIANTS = {"أساسي": "أساسي", "ثانوي": "ثانوي", "نجاح": "نجاح", "تحذير": "تحذير", "خطر": "خطر", "معلومات": "معلومات"}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_\-\u0600-\u06ff]+$")


def _text(interpreter: Interpreter, value: Any) -> str:
    return escape(interpreter.format_value(value), quote=True)


def _raw(interpreter: Interpreter, value: Any) -> str:
    return interpreter.format_value(value)


def _variant(interpreter: Interpreter, value: Any, node: Call, permitted: set[str]) -> str:
    if not isinstance(value, str) or value not in permitted:
        allowed = "، ".join(sorted(permitted))
        interpreter.error(node, f"نمط الواجهة يجب أن يكون أحد: {allowed}.")
    return value


def _identifier(interpreter: Interpreter, value: Any, node: Call) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        interpreter.error(node, "معرف المكوّن يجب أن يتألف من حروف أو أرقام أو شرطة أو شرطة سفلية فقط.")
    return value


def install_ui_builtins(interpreter: Interpreter) -> None:
    """يسجل مكونات واجهة نُطْق في بيئة المفسر."""

    def assets(_args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        return '<link rel="stylesheet" href="/_نطق/ui.css"><script src="/_نطق/ui.js" defer></script>'

    def icon(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        name = args[0]
        if not isinstance(name, str) or name not in ICON_PATHS:
            interpreter.error(node, "اسم الأيقونة غير معروف. الأسماء المتاحة: " + "، ".join(ICON_PATHS))
        size = args[1] if len(args) == 2 else 20
        if not isinstance(size, int) or isinstance(size, bool) or not 12 <= size <= 96:
            interpreter.error(node, "حجم الأيقونة يجب أن يكون عددًا صحيحًا بين 12 و96.")
        return f'<svg class="ن-أيقونة" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">{ICON_PATHS[name]}</svg>'

    def button(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        variant = _variant(interpreter, args[1] if len(args) == 2 else "أساسي", node, {"أساسي", "ثانوي", "نجاح", "خطر"})
        return f'<button type="button" class="ن-زر ن-زر--{variant}">{_text(interpreter, args[0])}</button>'

    def badge(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        variant = _variant(interpreter, args[1] if len(args) == 2 else "معلومات", node, {"معلومات", "ثانوي", "نجاح", "تحذير", "خطر"})
        return f'<span class="ن-شارة ن-شارة--{variant}">{_text(interpreter, args[0])}</span>'

    def alert(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        variant = _variant(interpreter, args[1] if len(args) == 2 else "معلومات", node, {"معلومات", "نجاح", "تحذير", "خطر"})
        return f'<aside class="ن-تنبيه ن-تنبيه--{variant}" role="alert">{_text(interpreter, args[0])}<button class="ن-تنبيه__إغلاق" data-نطق-إغلاق aria-label="إغلاق">×</button></aside>'

    def card(args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        footer = f'<footer class="ن-بطاقة__تذييل">{_raw(interpreter, args[2])}</footer>' if len(args) == 3 else ""
        return f'<article class="ن-بطاقة"><header class="ن-بطاقة__رأس"><h2 class="ن-بطاقة__عنوان">{_text(interpreter, args[0])}</h2></header><div class="ن-بطاقة__محتوى">{_raw(interpreter, args[1])}</div>{footer}</article>'

    def modal_button(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        component_id = _identifier(interpreter, args[0], node)
        return f'<button type="button" class="ن-زر" data-نطق-نافذة="{component_id}">{_text(interpreter, args[1])}</button>'

    def modal(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        component_id = _identifier(interpreter, args[0], node)
        return f'<dialog class="ن-نافذة" id="{component_id}"><header class="ن-نافذة__رأس"><h2 class="ن-نافذة__عنوان">{_text(interpreter, args[1])}</h2><button class="ن-نافذة__إغلاق" data-نطق-أغلق-نافذة aria-label="إغلاق">×</button></header><div class="ن-نافذة__محتوى">{_raw(interpreter, args[2])}</div></dialog>'

    def tabs(args: list[Any], _interpreter: Interpreter, node: Call) -> str:
        entries = args[0]
        if not isinstance(entries, list) or not entries:
            interpreter.error(node, "الدالة «تبويبات» تتطلب قائمة غير فارغة من القواميس.")
        buttons: list[str] = []
        panels: list[str] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or "عنوان" not in entry or "محتوى" not in entry:
                interpreter.error(node, "كل تبويب يجب أن يكون قاموسًا يحوي «عنوان» و«محتوى».")
            panel_id = f"ن-لوح-{index}"
            selected = "true" if index == 0 else "false"
            hidden = "" if index == 0 else " hidden"
            buttons.append(f'<button class="ن-تبويبات__زر" data-نطق-تبويب aria-selected="{selected}" aria-controls="{panel_id}">{_text(interpreter, entry["عنوان"])}</button>')
            panels.append(f'<section class="ن-تبويبات__لوح" id="{panel_id}" role="tabpanel"{hidden}>{_raw(interpreter, entry["محتوى"])}</section>')
        return '<section class="ن-تبويبات"><div class="ن-تبويبات__قائمة" role="tablist">' + "".join(buttons) + '</div>' + "".join(panels) + '</section>'

    def theme_button(args: list[Any], _interpreter: Interpreter, _node: Call) -> str:
        label = _text(interpreter, args[0] if args else "تبديل السمة")
        return f'<button type="button" class="ن-زر ن-زر--ثانوي" data-نطق-سمة>{label}</button>'

    interpreter._builtin("أصول_واجهة", 0, 0, assets)
    interpreter._builtin("أيقونة", 1, 2, icon)
    interpreter._builtin("زر", 1, 2, button)
    interpreter._builtin("شارة", 1, 2, badge)
    interpreter._builtin("تنبيه", 1, 2, alert)
    interpreter._builtin("بطاقة", 2, 3, card)
    interpreter._builtin("زر_نافذة", 2, 2, modal_button)
    interpreter._builtin("نافذة", 3, 3, modal)
    interpreter._builtin("تبويبات", 1, 1, tabs)
    interpreter._builtin("زر_سمة", 0, 1, theme_button)
