"""نواة لغة نُطْق: محلّل معجمي ونحوي ومفسّر عربي قابل للتوسعة."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
import unicodedata


# ============================== الأخطاء والرموز ==============================

class NutaqError(Exception):
    """خطأ قابل للعرض لمستخدم لغة نُطْق."""

    def __init__(self, kind: str, message: str, line: int, column: int):
        self.kind = kind
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{kind} (سطر {line}، عمود {column}): {message}")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


KEYWORDS = {
    "دع": "DECLARE",
    "دالة": "FUNCTION",
    "أرجع": "RETURN",
    "إذا": "IF",
    "وإلا": "ELSE",
    "بينما": "WHILE",
    "لكل": "FOR",
    "في": "IN",
    "توقف": "BREAK",
    "تابع": "CONTINUE",
    "استورد": "IMPORT",
    "ك": "AS",
    "صنف": "CLASS",
    "حاول": "TRY",
    "التقط": "CATCH",
    "أخيرًا": "FINALLY",
    "ارم": "THROW",
    "صحيح": "TRUE",
    "خطأ": "FALSE",
    "عدم": "NIL",
    "و": "OP",
    "أو": "OP",
    "ليس": "OP",
}

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789.")


class Lexer:
    """يحوّل النص العربي إلى قائمة رموز مرفقة بمواقعها."""

    def __init__(self, source: str):
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1
        self.tokens: list[Token] = []

    def scan_tokens(self) -> list[Token]:
        while not self._at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()
        self.tokens.append(Token("EOF", "", self.line, self.column))
        return self.tokens

    def _at_end(self) -> bool:
        return self.current >= len(self.source)

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _peek(self) -> str:
        return "\0" if self._at_end() else self.source[self.current]

    def _peek_next(self) -> str:
        return "\0" if self.current + 1 >= len(self.source) else self.source[self.current + 1]

    def _match(self, expected: str) -> bool:
        if self._at_end() or self.source[self.current] != expected:
            return False
        self._advance()
        return True

    def _add(self, kind: str, value: Optional[str] = None) -> None:
        if value is None:
            value = self.source[self.start:self.current]
        self.tokens.append(Token(kind, value, self.start_line, self.start_column))

    def _scan_token(self) -> None:
        char = self._advance()
        if char in " \t\f\v":
            return
        if char == "\n":
            self._add("NEWLINE", "\n")
            return
        if char == "#":
            while self._peek() not in "\n\0":
                self._advance()
            return
        if char in "()[]{}:.":
            self._add("PUNCT", char)
            return
        if char in ",،":
            self._add("COMMA", char)
            return
        if char in ";؛":
            self._add("SEMI", char)
            return
        if char in "+-*/%^":
            self._add("OP", char)
            return
        if char == "=":
            self._add("OP", "==" if self._match("=") else "=")
            return
        if char == "!":
            if self._match("="):
                self._add("OP", "!=")
                return
            self._error("الرمز ! لا يستخدم منفردًا؛ استخدم ليس أو !=.")
        if char == "<":
            self._add("OP", "<=" if self._match("=") else "<")
            return
        if char == ">":
            self._add("OP", ">=" if self._match("=") else ">")
            return
        if char in "\"'":
            self._string(char)
            return
        if char.isdigit():
            self._number()
            return
        if char.isalpha() or char == "_":
            self._identifier()
            return
        self._error(f"المحرف «{char}» غير معروف.")

    def _string(self, quote: str) -> None:
        value: list[str] = []
        while not self._at_end() and self._peek() != quote:
            char = self._advance()
            if char == "\\":
                if self._at_end():
                    self._error("تسلسل هروب غير مكتمل داخل النص.")
                escaped = self._advance()
                value.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "\"": "\"", "'": "'"}.get(escaped, escaped))
            else:
                value.append(char)
        if self._at_end():
            self._error("نص غير مغلق.")
        self._advance()  # الاقتباس الختامي
        self._add("STRING", "".join(value))

    def _number(self) -> None:
        while self._peek().isdigit():
            self._advance()
        if self._peek() in ".٫" and self._peek_next().isdigit():
            self._advance()
            while self._peek().isdigit():
                self._advance()
        raw = self.source[self.start:self.current].translate(ARABIC_DIGITS)
        self._add("NUMBER", raw)

    def _identifier(self) -> None:
        while self._is_identifier_part(self._peek()):
            self._advance()
        text = self.source[self.start:self.current]
        self._add(KEYWORDS.get(text, "IDENT"), text)

    @staticmethod
    def _is_identifier_part(char: str) -> bool:
        return char.isalpha() or char.isdigit() or char == "_" or unicodedata.category(char).startswith("M")

    def _error(self, message: str) -> None:
        raise NutaqError("خطأ_رمزي", message, self.start_line, self.start_column)


# ============================== شجرة الصياغة ==============================

@dataclass
class Node:
    line: int
    column: int


@dataclass
class Program(Node):
    statements: list[Node]


@dataclass
class Block(Node):
    statements: list[Node]


@dataclass
class Declare(Node):
    name: Token
    value: Optional[Node]


@dataclass
class Assign(Node):
    target: Node
    value: Node


@dataclass
class ExprStmt(Node):
    expression: Node


@dataclass
class If(Node):
    condition: Node
    then_branch: Block
    else_branch: Optional[Node]


@dataclass
class While(Node):
    condition: Node
    body: Block


@dataclass
class For(Node):
    name: Token
    iterable: Node
    body: Block


@dataclass
class Function(Node):
    name: Token
    parameters: list[Token]
    body: Block


@dataclass
class Import(Node):
    path: Token
    alias: Token


@dataclass
class Class(Node):
    name: Token
    methods: list[Function]


@dataclass
class Try(Node):
    body: Block
    error_name: Optional[Token]
    catch_body: Optional[Block]
    finally_body: Optional[Block]


@dataclass
class Throw(Node):
    value: Node


@dataclass
class Return(Node):
    value: Optional[Node]


@dataclass
class Break(Node):
    pass


@dataclass
class Continue(Node):
    pass


@dataclass
class Literal(Node):
    value: Any


@dataclass
class Variable(Node):
    name: Token


@dataclass
class Unary(Node):
    operator: Token
    right: Node


@dataclass
class Binary(Node):
    left: Node
    operator: Token
    right: Node


@dataclass
class Logical(Node):
    left: Node
    operator: Token
    right: Node


@dataclass
class Call(Node):
    callee: Node
    paren: Token
    arguments: list[Node]


@dataclass
class Index(Node):
    object: Node
    bracket: Token
    index: Node


@dataclass
class GetAttr(Node):
    object: Node
    name: Token


@dataclass
class ListLiteral(Node):
    elements: list[Node]


@dataclass
class DictLiteral(Node):
    entries: list[tuple[Node, Node]]


# ============================== المحلّل النحوي ==============================

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self._contextual_identifiers: list[str] = []

    def parse(self) -> Program:
        statements: list[Node] = []
        self._skip_separators()
        while not self._is_at_end():
            statements.append(self._statement())
            self._skip_separators()
        return Program(1, 1, statements)

    def _statement(self) -> Node:
        if self._match_kind("DECLARE"):
            return self._declaration(self._previous())
        if self._match_kind("FUNCTION"):
            return self._function(self._previous())
        if self._match_kind("IMPORT"):
            return self._import_statement(self._previous())
        if self._match_kind("CLASS"):
            return self._class_statement(self._previous())
        if self._match_kind("TRY"):
            return self._try_statement(self._previous())
        if self._match_kind("THROW"):
            return self._throw_statement(self._previous())
        if self._match_kind("IF"):
            return self._if_statement(self._previous())
        if self._match_kind("WHILE"):
            return self._while_statement(self._previous())
        if self._match_kind("FOR"):
            return self._for_statement(self._previous())
        if self._match_kind("RETURN"):
            return self._return_statement(self._previous())
        if self._match_kind("BREAK"):
            token = self._previous()
            return Break(token.line, token.column)
        if self._match_kind("CONTINUE"):
            token = self._previous()
            return Continue(token.line, token.column)
        expression = self._expression()
        if self._match_value("="):
            equals = self._previous()
            value = self._expression()
            if not isinstance(expression, (Variable, Index, GetAttr)):
                self._error(equals, "الجانب الأيسر من الإسناد يجب أن يكون اسمًا أو فهرسة أو خاصية.")
            return Assign(expression.line, expression.column, expression, value)
        return ExprStmt(expression.line, expression.column, expression)

    def _declaration(self, keyword: Token) -> Declare:
        name = self._consume_kind("IDENT", "توقعت اسمًا بعد «دع».")
        value = self._expression() if self._match_value("=") else None
        return Declare(keyword.line, keyword.column, name, value)

    def _function(self, keyword: Token) -> Function:
        name = self._consume_kind("IDENT", "توقعت اسم الدالة بعد «دالة».")
        self._consume_value("(", "توقعت ( بعد اسم الدالة.")
        parameters: list[Token] = []
        if not self._check_value(")"):
            while True:
                parameters.append(self._consume_kind("IDENT", "توقعت اسم معامل."))
                if not self._match_kind("COMMA"):
                    break
        self._consume_value(")", "توقعت ) بعد معاملات الدالة.")
        body = self._block()
        return Function(keyword.line, keyword.column, name, parameters, body)

    def _import_statement(self, keyword: Token) -> Import:
        path = self._consume_kind("STRING", "توقعت مسار وحدة نصيًا بعد «استورد».")
        self._consume_kind("AS", "توقعت الكلمة «ك» ثم اسمًا مستعارًا للوحدة.")
        alias = self._consume_kind("IDENT", "توقعت اسمًا مستعارًا للوحدة بعد «ك».")
        return Import(keyword.line, keyword.column, path, alias)

    def _class_statement(self, keyword: Token) -> Class:
        name = self._consume_kind("IDENT", "توقعت اسمًا بعد «صنف».")
        self._consume_value("{", "توقعت { لبداية تعريف الصنف.")
        methods: list[Function] = []
        self._skip_separators()
        while not self._check_value("}") and not self._is_at_end():
            if not self._match_kind("FUNCTION"):
                self._error(self._peek(), "يحتوي الصنف على تعريفات «دالة» فقط في هذا الإصدار.")
            methods.append(self._function(self._previous()))
            self._skip_separators()
        self._consume_value("}", "توقعت } لإغلاق تعريف الصنف.")
        return Class(keyword.line, keyword.column, name, methods)

    def _try_statement(self, keyword: Token) -> Try:
        body = self._block()
        self._skip_separators()
        error_name: Optional[Token] = None
        catch_body: Optional[Block] = None
        finally_body: Optional[Block] = None
        if self._match_kind("CATCH"):
            # يسمح باسم «خطأ» رغم كونه القيمة المنطقية المحجوزة الافتراضية.
            if self._check_kind("IDENT", "FALSE"):
                error_name = self._advance()
            if error_name is not None:
                self._contextual_identifiers.append(error_name.value)
            try:
                catch_body = self._block()
            finally:
                if error_name is not None:
                    self._contextual_identifiers.pop()
            self._skip_separators()
        if self._match_kind("FINALLY"):
            finally_body = self._block()
        if catch_body is None and finally_body is None:
            self._error(self._peek(), "توقعت «التقط» أو «أخيرًا» بعد كتلة «حاول».")
        return Try(keyword.line, keyword.column, body, error_name, catch_body, finally_body)

    def _throw_statement(self, keyword: Token) -> Throw:
        if self._check_separator_or_block_end():
            self._error(keyword, "توقعت قيمة بعد «ارم».")
        return Throw(keyword.line, keyword.column, self._expression())

    def _if_statement(self, keyword: Token) -> If:
        condition = self._expression()
        then_branch = self._block()
        else_branch: Optional[Node] = None
        self._skip_separators()
        if self._match_kind("ELSE"):
            if self._match_kind("IF"):
                else_branch = self._if_statement(self._previous())
            else:
                else_branch = self._block()
        return If(keyword.line, keyword.column, condition, then_branch, else_branch)

    def _while_statement(self, keyword: Token) -> While:
        condition = self._expression()
        return While(keyword.line, keyword.column, condition, self._block())

    def _for_statement(self, keyword: Token) -> For:
        name = self._consume_kind("IDENT", "توقعت اسم متغير بعد «لكل».")
        self._consume_kind("IN", "توقعت الكلمة «في» داخل حلقة لكل.")
        iterable = self._expression()
        return For(keyword.line, keyword.column, name, iterable, self._block())

    def _return_statement(self, keyword: Token) -> Return:
        value = None if self._check_separator_or_block_end() else self._expression()
        return Return(keyword.line, keyword.column, value)

    def _block(self) -> Block:
        opening = self._consume_value("{", "توقعت { لبداية الكتلة.")
        statements: list[Node] = []
        self._skip_separators()
        while not self._check_value("}") and not self._is_at_end():
            statements.append(self._statement())
            self._skip_separators()
        self._consume_value("}", "توقعت } لإغلاق الكتلة.")
        return Block(opening.line, opening.column, statements)

    def _expression(self) -> Node:
        return self._or()

    def _or(self) -> Node:
        expression = self._and()
        while self._match_value("أو"):
            operator = self._previous()
            expression = Logical(expression.line, expression.column, expression, operator, self._and())
        return expression

    def _and(self) -> Node:
        expression = self._equality()
        while self._match_value("و"):
            operator = self._previous()
            expression = Logical(expression.line, expression.column, expression, operator, self._equality())
        return expression

    def _equality(self) -> Node:
        expression = self._comparison()
        while self._match_value("==", "!="):
            operator = self._previous()
            expression = Binary(expression.line, expression.column, expression, operator, self._comparison())
        return expression

    def _comparison(self) -> Node:
        expression = self._term()
        while self._match_value("<", "<=", ">", ">="):
            operator = self._previous()
            expression = Binary(expression.line, expression.column, expression, operator, self._term())
        return expression

    def _term(self) -> Node:
        expression = self._factor()
        while self._match_value("+", "-"):
            operator = self._previous()
            expression = Binary(expression.line, expression.column, expression, operator, self._factor())
        return expression

    def _factor(self) -> Node:
        expression = self._power()
        while self._match_value("*", "/", "%"):
            operator = self._previous()
            expression = Binary(expression.line, expression.column, expression, operator, self._power())
        return expression

    def _power(self) -> Node:
        expression = self._unary()
        if self._match_value("^"):
            operator = self._previous()
            expression = Binary(expression.line, expression.column, expression, operator, self._power())
        return expression

    def _unary(self) -> Node:
        if self._match_value("-", "ليس"):
            operator = self._previous()
            right = self._unary()
            return Unary(operator.line, operator.column, operator, right)
        return self._call()

    def _call(self) -> Node:
        expression = self._primary()
        while True:
            if self._match_value("("):
                paren = self._previous()
                arguments: list[Node] = []
                self._skip_separators()
                if not self._check_value(")"):
                    while True:
                        arguments.append(self._expression())
                        self._skip_separators()
                        if not self._match_kind("COMMA"):
                            break
                        self._skip_separators()
                self._consume_value(")", "توقعت ) بعد وسائط الاستدعاء.")
                expression = Call(expression.line, expression.column, expression, paren, arguments)
            elif self._match_value("["):
                bracket = self._previous()
                index = self._expression()
                self._consume_value("]", "توقعت ] بعد الفهرس.")
                expression = Index(expression.line, expression.column, expression, bracket, index)
            elif self._match_value("."):
                name = self._consume_kind("IDENT", "توقعت اسم خاصية بعد النقطة.")
                expression = GetAttr(expression.line, expression.column, expression, name)
            else:
                break
        return expression

    def _primary(self) -> Node:
        token = self._advance()
        if token.kind == "NUMBER":
            value: Any = float(token.value) if "." in token.value else int(token.value)
            return Literal(token.line, token.column, value)
        if token.kind == "STRING":
            return Literal(token.line, token.column, token.value)
        if token.kind == "TRUE":
            return Literal(token.line, token.column, True)
        if token.kind == "FALSE":
            if token.value in self._contextual_identifiers:
                return Variable(token.line, token.column, Token("IDENT", token.value, token.line, token.column))
            return Literal(token.line, token.column, False)
        if token.kind == "NIL":
            return Literal(token.line, token.column, None)
        if token.kind == "IDENT":
            return Variable(token.line, token.column, token)
        if token.value == "(":
            expression = self._expression()
            self._consume_value(")", "توقعت ) بعد التعبير.")
            return expression
        if token.value == "[":
            return self._list_literal(token)
        if token.value == "{":
            return self._dict_literal(token)
        self._error(token, "توقعت قيمة أو اسمًا أو تعبيرًا بين قوسين.")
        raise AssertionError("غير قابل للوصول")

    def _list_literal(self, opening: Token) -> ListLiteral:
        elements: list[Node] = []
        self._skip_separators()
        if not self._check_value("]"):
            while True:
                elements.append(self._expression())
                self._skip_separators()
                if not self._match_kind("COMMA"):
                    break
                self._skip_separators()
        self._consume_value("]", "توقعت ] بعد عناصر القائمة.")
        return ListLiteral(opening.line, opening.column, elements)

    def _dict_literal(self, opening: Token) -> DictLiteral:
        entries: list[tuple[Node, Node]] = []
        self._skip_separators()
        if not self._check_value("}"):
            while True:
                key = self._expression()
                self._consume_value(":", "توقعت : بين مفتاح القاموس وقيمته.")
                value = self._expression()
                entries.append((key, value))
                self._skip_separators()
                if not self._match_kind("COMMA"):
                    break
                self._skip_separators()
        self._consume_value("}", "توقعت } بعد عناصر القاموس.")
        return DictLiteral(opening.line, opening.column, entries)

    def _skip_separators(self) -> None:
        while self._check_kind("NEWLINE") or self._check_kind("SEMI"):
            self._advance()

    def _check_separator_or_block_end(self) -> bool:
        return self._check_kind("NEWLINE") or self._check_kind("SEMI") or self._check_value("}") or self._is_at_end()

    def _match_kind(self, *kinds: str) -> bool:
        if self._check_kind(*kinds):
            self._advance()
            return True
        return False

    def _match_value(self, *values: str) -> bool:
        if self._check_value(*values):
            self._advance()
            return True
        return False

    def _consume_kind(self, kind: str, message: str) -> Token:
        if self._check_kind(kind):
            return self._advance()
        self._error(self._peek(), message)
        raise AssertionError("غير قابل للوصول")

    def _consume_value(self, value: str, message: str) -> Token:
        if self._check_value(value):
            return self._advance()
        self._error(self._peek(), message)
        raise AssertionError("غير قابل للوصول")

    def _check_kind(self, *kinds: str) -> bool:
        return not self._is_at_end() and self._peek().kind in kinds

    def _check_value(self, *values: str) -> bool:
        # لا يجوز أن تتحول سلسلة مثل "-" أو ")" إلى عامل أو رمز بنيوي.
        return not self._is_at_end() and self._peek().kind != "STRING" and self._peek().value in values

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().kind == "EOF"

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> None:
        raise NutaqError("خطأ_نحوي", message, token.line, token.column)


# ============================== بيئة التنفيذ ==============================

class Environment:
    def __init__(self, parent: Optional["Environment"] = None):
        self.parent = parent
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, token: Token) -> Any:
        if token.value in self.values:
            return self.values[token.value]
        if self.parent is not None:
            return self.parent.get(token)
        raise NutaqError("خطأ_اسم", f"الاسم «{token.value}» غير معرّف.", token.line, token.column)

    def assign(self, token: Token, value: Any) -> None:
        """يحدّث الاسم الأقرب الموجود، أو ينشئه في النطاق الحالي إن لم يوجد."""
        environment: Optional[Environment] = self
        while environment is not None:
            if token.value in environment.values:
                environment.values[token.value] = value
                return
            environment = environment.parent
        self.values[token.value] = value


class ReturnSignal(Exception):
    def __init__(self, value: Any, line: int, column: int):
        self.value, self.line, self.column = value, line, column


class BreakSignal(Exception):
    def __init__(self, line: int, column: int):
        self.line, self.column = line, column


class ContinueSignal(Exception):
    def __init__(self, line: int, column: int):
        self.line, self.column = line, column


class ThrownSignal(Exception):
    """قيمة يرميها برنامج نُطْق ويمكن التقاطها بواسطة «التقط»."""

    def __init__(self, value: Any, line: int, column: int):
        self.value, self.line, self.column = value, line, column


class PropertyAccessible:
    """قيمة تدعم الوصول إلى خصائص نُطْق بالنقطة."""

    def get_property(self, interpreter: "Interpreter", name: Token, node: Node) -> Any:
        raise NotImplementedError

    def set_property(self, interpreter: "Interpreter", name: Token, value: Any, node: Node) -> None:
        interpreter.error(node, f"لا يمكن تعديل الخاصية «{name.value}».")


class CallableValue:
    def call(self, interpreter: "Interpreter", arguments: list[Any], node: Call) -> Any:
        raise NotImplementedError

    def arity_text(self) -> str:
        return ""


class NutaqModule(PropertyAccessible):
    """فضاء أسماء لوحدة محلية محمّلة بعبارة «استورد»."""

    def __init__(self, name: str, environment: Environment):
        self.name = name
        self.environment = environment

    def get_property(self, interpreter: "Interpreter", name: Token, node: Node) -> Any:
        if name.value in self.environment.values:
            return self.environment.values[name.value]
        interpreter.error(node, f"الوحدة «{self.name}» لا تصدّر الاسم «{name.value}».")

    def __str__(self) -> str:
        return f"<وحدة {self.name}>"


class NutaqFunction(CallableValue):
    def __init__(self, declaration: Function, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    def call(self, interpreter: "Interpreter", arguments: list[Any], node: Call) -> Any:
        expected = len(self.declaration.parameters)
        if len(arguments) != expected:
            interpreter.error(node, f"الدالة «{self.declaration.name.value}» تتوقع {expected} وسيطًا، لا {len(arguments)}.")
        environment = Environment(self.closure)
        for parameter, argument in zip(self.declaration.parameters, arguments):
            environment.define(parameter.value, argument)
        try:
            interpreter.execute_block(self.declaration.body.statements, environment)
        except ReturnSignal as signal:
            return signal.value
        return None

    def __str__(self) -> str:
        return f"<دالة {self.declaration.name.value}>"


class BoundMethod(CallableValue):
    """دالة صف مرتبطة بكائن، فتتلقى «ذات» تلقائيًا."""

    def __init__(self, instance: "NutaqInstance", function: NutaqFunction):
        self.instance = instance
        self.function = function

    def call(self, interpreter: "Interpreter", arguments: list[Any], node: Call) -> Any:
        return self.function.call(interpreter, [self.instance, *arguments], node)

    def __str__(self) -> str:
        return f"<طريقة {self.function.declaration.name.value}>"


class NutaqClass(CallableValue):
    def __init__(self, name: str, methods: dict[str, NutaqFunction]):
        self.name = name
        self.methods = methods

    def call(self, interpreter: "Interpreter", arguments: list[Any], node: Call) -> Any:
        instance = NutaqInstance(self)
        initializer = self.methods.get("تهيئة")
        if initializer is not None:
            initializer.call(interpreter, [instance, *arguments], node)
        elif arguments:
            interpreter.error(node, f"الصنف «{self.name}» لا يملك «تهيئة» لكنه تلقى وسائط.")
        return instance

    def __str__(self) -> str:
        return f"<صنف {self.name}>"


class NutaqInstance(PropertyAccessible):
    def __init__(self, klass: NutaqClass):
        self.klass = klass
        self.fields: dict[str, Any] = {}

    def get_property(self, interpreter: "Interpreter", name: Token, node: Node) -> Any:
        if name.value in self.fields:
            return self.fields[name.value]
        method = self.klass.methods.get(name.value)
        if method is not None:
            return BoundMethod(self, method)
        interpreter.error(node, f"الكائن من الصنف «{self.klass.name}» لا يملك الخاصية «{name.value}».")

    def set_property(self, _interpreter: "Interpreter", name: Token, value: Any, _node: Node) -> None:
        self.fields[name.value] = value

    def __str__(self) -> str:
        return f"<كائن {self.klass.name}>"


class NativeFunction(CallableValue):
    def __init__(self, name: str, minimum: int, maximum: Optional[int], implementation: Callable[[list[Any], "Interpreter", Call], Any]):
        self.name = name
        self.minimum = minimum
        self.maximum = maximum
        self.implementation = implementation

    def call(self, interpreter: "Interpreter", arguments: list[Any], node: Call) -> Any:
        if len(arguments) < self.minimum or (self.maximum is not None and len(arguments) > self.maximum):
            if self.minimum == self.maximum:
                expectation = f"{self.minimum} وسيطًا"
            elif self.maximum is None:
                expectation = f"{self.minimum} وسيط أو أكثر"
            else:
                expectation = f"من {self.minimum} إلى {self.maximum} وسائط"
            interpreter.error(node, f"الدالة «{self.name}» تتوقع {expectation}، لا {len(arguments)}.")
        return self.implementation(arguments, interpreter, node)

    def __str__(self) -> str:
        return f"<دالة_مدمجة {self.name}>"


# ============================== المفسّر والمكتبة المعيارية ==============================

class Interpreter:
    def __init__(
        self,
        output: Optional[Callable[[str], None]] = None,
        input_provider: Optional[Callable[[str], str]] = None,
        project_dir: Optional[str | Path] = None,
    ):
        self.output = output or print
        self.input_provider = input_provider or input
        self.project_dir = Path(project_dir or ".").resolve()
        self.globals = Environment()
        self.environment = self.globals
        self.module_cache: dict[Path, NutaqModule] = {}
        self._install_builtins()

    def interpret(self, program: Program) -> Any:
        try:
            result: Any = None
            for statement in program.statements:
                result = self.evaluate(statement)
            return result
        except ReturnSignal as signal:
            raise NutaqError("خطأ_تنفيذي", "لا يجوز استعمال «أرجع» خارج دالة.", signal.line, signal.column) from None
        except BreakSignal as signal:
            raise NutaqError("خطأ_تنفيذي", "لا يجوز استعمال «توقف» خارج حلقة.", signal.line, signal.column) from None
        except ContinueSignal as signal:
            raise NutaqError("خطأ_تنفيذي", "لا يجوز استعمال «تابع» خارج حلقة.", signal.line, signal.column) from None
        except ThrownSignal as signal:
            raise NutaqError("خطأ_مرمي", f"قيمة غير معالجة: {self.format_value(signal.value)}", signal.line, signal.column) from None

    def execute_block(self, statements: list[Node], environment: Environment) -> Any:
        previous = self.environment
        try:
            self.environment = environment
            result: Any = None
            for statement in statements:
                result = self.evaluate(statement)
            return result
        finally:
            self.environment = previous

    def evaluate(self, node: Node) -> Any:
        method = getattr(self, f"visit_{type(node).__name__}")
        return method(node)

    def visit_Program(self, node: Program) -> Any:
        return self.interpret(node)

    def visit_Block(self, node: Block) -> Any:
        return self.execute_block(node.statements, Environment(self.environment))

    def visit_Declare(self, node: Declare) -> Any:
        self.environment.define(node.name.value, self.evaluate(node.value) if node.value is not None else None)
        return None

    def visit_Assign(self, node: Assign) -> Any:
        value = self.evaluate(node.value)
        if isinstance(node.target, Variable):
            self.environment.assign(node.target.name, value)
            return value
        if isinstance(node.target, Index):
            container = self.evaluate(node.target.object)
            index = self.evaluate(node.target.index)
            self._set_index(container, index, value, node)
            return value
        if isinstance(node.target, GetAttr):
            container = self.evaluate(node.target.object)
            self._set_property(container, node.target.name, value, node)
            return value
        self.error(node, "هدف إسناد غير صالح.")

    def visit_ExprStmt(self, node: ExprStmt) -> Any:
        return self.evaluate(node.expression)

    def visit_If(self, node: If) -> Any:
        if self.is_truthy(self.evaluate(node.condition)):
            return self.evaluate(node.then_branch)
        if node.else_branch is not None:
            return self.evaluate(node.else_branch)
        return None

    def visit_While(self, node: While) -> Any:
        result: Any = None
        while self.is_truthy(self.evaluate(node.condition)):
            try:
                result = self.evaluate(node.body)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def visit_For(self, node: For) -> Any:
        iterable = self.evaluate(node.iterable)
        if isinstance(iterable, dict):
            values = list(iterable.keys())
        elif isinstance(iterable, (list, str)):
            values = list(iterable)
        else:
            self.error(node.iterable, f"القيمة من النوع «{self.type_name(iterable)}» غير قابلة للمرور.")
        result: Any = None
        for value in values:
            loop_environment = Environment(self.environment)
            loop_environment.define(node.name.value, value)
            try:
                result = self.execute_block(node.body.statements, loop_environment)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return result

    def visit_Function(self, node: Function) -> Any:
        self.environment.define(node.name.value, NutaqFunction(node, self.environment))
        return None

    def visit_Import(self, node: Import) -> Any:
        self.environment.define(node.alias.value, self.load_module(node.path.value, node))
        return None

    def visit_Class(self, node: Class) -> Any:
        # نعرّف الاسم أولًا كي تتمكن الطرائق من الإشارة إلى الصنف تراجعيًا.
        methods = {method.name.value: NutaqFunction(method, self.environment) for method in node.methods}
        self.environment.define(node.name.value, NutaqClass(node.name.value, methods))
        return None

    def visit_Try(self, node: Try) -> Any:
        result: Any = None
        try:
            try:
                result = self.evaluate(node.body)
            except (ThrownSignal, NutaqError) as failure:
                if node.catch_body is None:
                    raise
                if isinstance(failure, ThrownSignal):
                    error_value = {
                        "نوع": "خطأ_مرمي",
                        "رسالة": self.format_value(failure.value),
                        "قيمة": failure.value,
                    }
                else:
                    error_value = {
                        "نوع": failure.kind,
                        "رسالة": failure.message,
                        "سطر": failure.line,
                        "عمود": failure.column,
                    }
                catch_environment = Environment(self.environment)
                if node.error_name is not None:
                    catch_environment.define(node.error_name.value, error_value)
                result = self.execute_block(node.catch_body.statements, catch_environment)
        finally:
            if node.finally_body is not None:
                result = self.evaluate(node.finally_body)
        return result

    def visit_Throw(self, node: Throw) -> Any:
        raise ThrownSignal(self.evaluate(node.value), node.line, node.column)

    def visit_Return(self, node: Return) -> Any:
        raise ReturnSignal(self.evaluate(node.value) if node.value is not None else None, node.line, node.column)

    def visit_Break(self, node: Break) -> Any:
        raise BreakSignal(node.line, node.column)

    def visit_Continue(self, node: Continue) -> Any:
        raise ContinueSignal(node.line, node.column)

    def visit_Literal(self, node: Literal) -> Any:
        return node.value

    def visit_Variable(self, node: Variable) -> Any:
        return self.environment.get(node.name)

    def visit_Unary(self, node: Unary) -> Any:
        right = self.evaluate(node.right)
        if node.operator.value == "ليس":
            return not self.is_truthy(right)
        if node.operator.value == "-":
            self.require_number(node, right)
            return -right
        self.error(node, "عامل أحادي غير معروف.")

    def visit_Logical(self, node: Logical) -> Any:
        left = self.evaluate(node.left)
        if node.operator.value == "أو":
            return left if self.is_truthy(left) else self.evaluate(node.right)
        return self.evaluate(node.right) if self.is_truthy(left) else left

    def visit_Binary(self, node: Binary) -> Any:
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        operator = node.operator.value
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator in ("<", "<=", ">", ">="):
            if (self.is_number(left) and self.is_number(right)) or (isinstance(left, str) and isinstance(right, str)):
                return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[operator]
            self.error(node, "المقارنة الترتيبية تتطلب عددين أو نصين.")
        if operator == "+":
            if self.is_number(left) and self.is_number(right):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            self.error(node, "العامل + يتطلب عددين أو نصين أو قائمتين من النوع نفسه.")
        if operator in ("-", "*", "/", "%", "^"):
            self.require_number(node, left, right)
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if operator == "/":
                if right == 0:
                    self.error(node, "لا يمكن القسمة على صفر.")
                return left / right
            if operator == "%":
                if right == 0:
                    self.error(node, "لا يمكن أخذ باقي القسمة على صفر.")
                return left % right
            return left ** right
        self.error(node, f"العامل «{operator}» غير معروف.")

    def visit_Call(self, node: Call) -> Any:
        callee = self.evaluate(node.callee)
        if not isinstance(callee, CallableValue):
            self.error(node, f"القيمة من النوع «{self.type_name(callee)}» لا يمكن استدعاؤها.")
        arguments = [self.evaluate(argument) for argument in node.arguments]
        return callee.call(self, arguments, node)

    def visit_Index(self, node: Index) -> Any:
        container = self.evaluate(node.object)
        index = self.evaluate(node.index)
        return self._get_index(container, index, node)

    def visit_GetAttr(self, node: GetAttr) -> Any:
        container = self.evaluate(node.object)
        return self._get_property(container, node.name, node)

    def visit_ListLiteral(self, node: ListLiteral) -> Any:
        return [self.evaluate(element) for element in node.elements]

    def visit_DictLiteral(self, node: DictLiteral) -> Any:
        result: dict[Any, Any] = {}
        for key_node, value_node in node.entries:
            key = self.evaluate(key_node)
            try:
                hash(key)
            except TypeError:
                self.error(key_node, "مفتاح القاموس يجب أن يكون عددًا أو نصًا أو قيمة منطقية.")
            result[key] = self.evaluate(value_node)
        return result

    def _get_index(self, container: Any, index: Any, node: Node) -> Any:
        if isinstance(container, dict):
            try:
                return container[index]
            except (KeyError, TypeError):
                self.error(node, f"المفتاح «{self.format_value(index)}» غير موجود في القاموس.")
        if isinstance(container, (list, str)):
            integer = self.require_integer(node, index, "فهرس القائمة أو النص")
            try:
                return container[integer]
            except IndexError:
                self.error(node, f"الفهرس {integer} خارج الحدود.")
        self.error(node, f"لا يمكن فهرسة قيمة من النوع «{self.type_name(container)}».")

    def _get_property(self, container: Any, name: Token, node: Node) -> Any:
        if isinstance(container, PropertyAccessible):
            return container.get_property(self, name, node)
        if isinstance(container, dict):
            if name.value in container:
                return container[name.value]
            self.error(node, f"القاموس لا يملك المفتاح «{name.value}».")
        self.error(node, f"القيمة من النوع «{self.type_name(container)}» لا تملك خصائص.")

    def _set_property(self, container: Any, name: Token, value: Any, node: Node) -> None:
        if isinstance(container, PropertyAccessible):
            container.set_property(self, name, value, node)
            return
        if isinstance(container, dict):
            container[name.value] = value
            return
        self.error(node, f"القيمة من النوع «{self.type_name(container)}» لا تقبل تعيين خصائص.")

    def _set_index(self, container: Any, index: Any, value: Any, node: Node) -> None:
        if isinstance(container, dict):
            try:
                hash(index)
            except TypeError:
                self.error(node, "مفتاح القاموس غير صالح.")
            container[index] = value
            return
        if isinstance(container, list):
            integer = self.require_integer(node, index, "فهرس القائمة")
            if not -len(container) <= integer < len(container):
                self.error(node, f"الفهرس {integer} خارج الحدود.")
            container[integer] = value
            return
        self.error(node, f"لا يمكن الإسناد عبر فهرسة قيمة من النوع «{self.type_name(container)}».")

    def load_module(self, requested_path: str, node: Node) -> NutaqModule:
        """يحمّل وحدة محلية مرة واحدة من داخل جذر المشروع فقط."""
        try:
            path = (self.project_dir / requested_path).resolve()
            if path != self.project_dir and self.project_dir not in path.parents:
                raise ValueError
        except (OSError, ValueError):
            self.error(node, "مسار الوحدة يجب أن يبقى داخل مجلد المشروع.")
        if path.suffix != ".نطق":
            self.error(node, "ملف الوحدة يجب أن يحمل امتداد .نطق.")
        cached = self.module_cache.get(path)
        if cached is not None:
            return cached
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.error(node, f"ملف الوحدة «{requested_path}» غير موجود.")
        except OSError as error:
            self.error(node, f"تعذر قراءة الوحدة «{requested_path}»: {error}")
        module_environment = Environment(self.globals)
        module = NutaqModule(path.stem, module_environment)
        self.module_cache[path] = module
        previous = self.environment
        try:
            self.environment = module_environment
            for statement in parse(source).statements:
                self.evaluate(statement)
        except Exception:
            self.module_cache.pop(path, None)
            raise
        finally:
            self.environment = previous
        return module

    def is_truthy(self, value: Any) -> bool:
        return bool(value)

    @staticmethod
    def is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def require_number(self, node: Node, *values: Any) -> None:
        if not all(self.is_number(value) for value in values):
            self.error(node, "هذه العملية تتطلب أعدادًا.")

    def require_integer(self, node: Node, value: Any, description: str) -> int:
        if not self.is_number(value) or int(value) != value:
            self.error(node, f"{description} يجب أن يكون عددًا صحيحًا.")
        return int(value)

    def type_name(self, value: Any) -> str:
        if value is None:
            return "عدم"
        if isinstance(value, bool):
            return "منطقي"
        if self.is_number(value):
            return "عدد"
        if isinstance(value, str):
            return "نص"
        if isinstance(value, list):
            return "قائمة"
        if isinstance(value, dict):
            return "قاموس"
        if isinstance(value, NutaqClass):
            return "صنف"
        if isinstance(value, NutaqInstance):
            return "كائن"
        if isinstance(value, NutaqModule):
            return "وحدة"
        if isinstance(value, CallableValue):
            return "دالة"
        return "مجهول"

    def format_value(self, value: Any, quoted: bool = False) -> str:
        if value is None:
            return "عدم"
        if value is True:
            return "صحيح"
        if value is False:
            return "خطأ"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, str):
            return f'"{value}"' if quoted else value
        if isinstance(value, list):
            return "[" + "، ".join(self.format_value(item, quoted=True) for item in value) + "]"
        if isinstance(value, dict):
            return "{" + "، ".join(f"{self.format_value(key, quoted=True)}: {self.format_value(item, quoted=True)}" for key, item in value.items()) + "}"
        return str(value)

    def error(self, node: Node, message: str) -> None:
        raise NutaqError("خطأ_تنفيذي", message, node.line, node.column)

    def _install_builtins(self) -> None:
        self._builtin("اطبع", 0, None, self._print)
        self._builtin("أدخل", 0, 1, self._input)
        self._builtin("طول", 1, 1, self._length)
        self._builtin("نطاق", 1, 3, self._range)
        self._builtin("عدد", 1, 1, self._number)
        self._builtin("نص", 1, 1, lambda args, _i, _n: self.format_value(args[0]))
        self._builtin("نوع", 1, 1, lambda args, _i, _n: self.type_name(args[0]))
        self._builtin("أضف", 2, 2, self._append)
        self._builtin("احذف", 2, 2, self._remove)
        self._builtin("مفاتيح", 1, 1, self._keys)
        self._builtin("قيم", 1, 1, self._values)
        # استيرادات محلية تمنع دورات الاستيراد بين النواة وملحقاتها.
        from .stdlib import install_standard_extensions
        from .web import install_web_builtins
        install_standard_extensions(self)
        install_web_builtins(self)

    def _builtin(self, name: str, minimum: int, maximum: Optional[int], implementation: Callable[[list[Any], "Interpreter", Call], Any]) -> None:
        self.globals.define(name, NativeFunction(name, minimum, maximum, implementation))

    def _print(self, args: list[Any], _interpreter: "Interpreter", _node: Call) -> None:
        self.output(" ".join(self.format_value(arg) for arg in args))
        return None

    def _input(self, args: list[Any], _interpreter: "Interpreter", _node: Call) -> str:
        prompt = self.format_value(args[0]) if args else ""
        return self.input_provider(prompt)

    def _length(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> int:
        if not isinstance(args[0], (str, list, dict)):
            self.error(node, "الدالة «طول» تتطلب نصًا أو قائمة أو قاموسًا.")
        return len(args[0])

    def _range(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> list[int]:
        values = [self.require_integer(node, value, "وسيط نطاق") for value in args]
        if len(values) == 1:
            start, stop, step = 0, values[0], 1
        elif len(values) == 2:
            start, stop, step = values[0], values[1], 1
        else:
            start, stop, step = values
        if step == 0:
            self.error(node, "خطوة «نطاق» لا يمكن أن تكون صفرًا.")
        return list(range(start, stop, step))

    def _number(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> Any:
        value = args[0]
        if self.is_number(value):
            return value
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, str):
            try:
                text = value.strip().translate(ARABIC_DIGITS)
                if not text:
                    raise ValueError
                return float(text) if "." in text else int(text)
            except ValueError:
                self.error(node, f"لا يمكن تحويل «{value}» إلى عدد.")
        self.error(node, f"لا يمكن تحويل النوع «{self.type_name(value)}» إلى عدد.")

    def _append(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> None:
        if not isinstance(args[0], list):
            self.error(node, "الوسيط الأول لـ«أضف» يجب أن يكون قائمة.")
        args[0].append(args[1])
        return None

    def _remove(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> Any:
        if not isinstance(args[0], list):
            self.error(node, "الوسيط الأول لـ«احذف» يجب أن يكون قائمة.")
        index = self.require_integer(node, args[1], "فهرس احذف")
        try:
            return args[0].pop(index)
        except IndexError:
            self.error(node, f"الفهرس {index} خارج الحدود.")

    def _keys(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> list[Any]:
        if not isinstance(args[0], dict):
            self.error(node, "الدالة «مفاتيح» تتطلب قاموسًا.")
        return list(args[0].keys())

    def _values(self, args: list[Any], _interpreter: "Interpreter", node: Call) -> list[Any]:
        if not isinstance(args[0], dict):
            self.error(node, "الدالة «قيم» تتطلب قاموسًا.")
        return list(args[0].values())


def parse(source: str) -> Program:
    """يحلّل نص نُطْق ويعيد شجرة البرنامج، أو يرمي NutaqError."""
    return Parser(Lexer(source).scan_tokens()).parse()


def run(
    source: str,
    output: Optional[Callable[[str], None]] = None,
    input_provider: Optional[Callable[[str], str]] = None,
    project_dir: Optional[str | Path] = None,
) -> Any:
    """ينفّذ مصدر نُطْق في بيئة جديدة، وهي دالة ملائمة للاختبارات والتضمين."""
    return Interpreter(output=output, input_provider=input_provider, project_dir=project_dir).interpret(parse(source))
