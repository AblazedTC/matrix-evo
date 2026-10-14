"""TI-BASIC subset simulator for Matrix Evo.

This is a test harness, not a calculator emulator. It runs the src/*.tib programs with
TI-84 style semantics for the commands Matrix Evo uses, so the mathematical logic,
menus and variable plumbing can be regression-tested off-device:

* 14-significant-digit decimal arithmetic (the TI float format)
* a 10 x 31 home screen (TI-84 Evo) for Output(/Disp/ClrHome
* scripted user input: Menu( choices, Input strings and getKey codes
* TI-BASIC control flow: If/Then/Else, For(, While, Repeat, Lbl/Goto, prgm calls

It deliberately rejects anything outside the subset (unknown tokens, Goto out of an
open block, empty lists, out-of-range indices) so that the source stays inside what
was audited against the Evo token table.
"""
from __future__ import annotations

import math
import re
from decimal import Decimal, Context, ROUND_HALF_EVEN, localcontext
from pathlib import Path

CTX = Context(prec=14, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999)
ROWS, COLS = 10, 31


class TIError(Exception):
    """A calculator error such as ERR:DOMAIN."""


class EndOfScript(Exception):
    """The program asked for input that the test script did not provide."""


class StopProgram(Exception):
    pass


class ReturnFromProgram(Exception):
    pass


def D(x) -> Decimal:
    return CTX.create_decimal(x)


# ---------------------------------------------------------------- tokenizer

FUNCS = [
    "toString(", "inString(", "identity(", "augment(", "remainder(", "rowSwap(",
    "length(", "round(", "fPart(", "iPart(", "expr(", "abs(", "int(", "gcd(", "max(",
    "min(", "not(", "dim(", "sub(", "sum(", "√(",
]
COMMANDS = [
    "ClrHome", "Output(", "Disp ", "Disp", "Pause ", "Pause", "Input ", "Menu(", "If ", "Then",
    "Else", "End", "For(", "While ", "Repeat ", "Return", "Stop", "Lbl ", "Goto ", "DelVar ",
    "Fill(", "Float", "Normal", "getKey",
]
OPS = [" and ", " xor ", " or ", "→", "≠", "≤", "≥", "=", "<", ">", "+", "-", "*", "/", "^",
       "⁻", "ᵀ", "²", "(", ")", "{", "}", ",", ":"]


def tokenize_line(line: str):
    """Split one source line into tokens (strings are kept as ('str', text))."""
    toks = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == '"':
            j = line.find('"', i + 1)
            if j < 0:
                j = n
            toks.append(("str", line[i + 1:j]))
            i = j + 1
            continue
        if line.startswith("prgm", i):
            m = re.match(r"prgm([A-Z][A-Z0-9]{0,7})", line[i:])
            if not m:
                raise TIError("ERR:SYNTAX bad prgm name")
            toks.append(("prgm", m.group(1)))
            i += m.end()
            continue
        m = re.match(r"(\d+\.?\d*|\.\d+)(ᴇ⁻?\d+)?|ᴇ⁻?\d+", line[i:])
        if m:
            text = m.group(0)
            if text.startswith("ᴇ"):
                text = "1" + text
            toks.append(("num", D(text.replace("ᴇ", "E").replace("⁻", "-"))))
            i += m.end()
            continue
        matched = False
        for word in COMMANDS + FUNCS + OPS:
            if line.startswith(word, i):
                if word in ("Disp", "Pause") and line.startswith(word + " ", i):
                    continue
                toks.append(("op", word))
                i += len(word)
                matched = True
                break
        if matched:
            continue
        m = re.match(r"Str[0-9]", line[i:])
        if m:
            toks.append(("strvar", m.group(0)))
            i += 4
            continue
        m = re.match(r"\[([A-J])\]", line[i:])
        if m:
            toks.append(("mat", m.group(1)))
            i += 3
            continue
        m = re.match(r"ʟ([A-Z][A-Z0-9]{0,4})", line[i:])
        if m:
            toks.append(("list", m.group(1)))
            i += m.end()
            continue
        if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZθ":
            toks.append(("var", c))
            i += 1
            continue
        if c == " ":
            raise TIError(f"ERR:SYNTAX stray space at col {i + 1}: {line!r}")
        raise TIError(f"ERR:SYNTAX unknown token {line[i:i + 8]!r} in {line!r}")
    return toks


def split_statements(text: str):
    """Program text -> list of token lists, one per statement (newline or ':')."""
    out = []
    for raw in text.split("\n"):
        if raw.strip().startswith("//") or not raw.strip():
            continue
        line = raw.rstrip()
        cur = []
        for tok in tokenize_line(line):
            if tok == ("op", ":"):
                out.append(cur)
                cur = []
            else:
                cur.append(tok)
        out.append(cur)
    return [s for s in out if s]


# ---------------------------------------------------------------- formatting

def fmt_num(x: Decimal) -> str:
    """TI Normal/Float display of a real number (10 significant digits)."""
    if x == 0:
        return "0"
    neg = x < 0
    a = abs(x)
    with localcontext(CTX) as c:
        c.prec = 10
        a = +a
    if a >= D("1E10") or a < D("0.001"):
        mant, exp = f"{a:.9E}".split("E")
        mant = mant.rstrip("0").rstrip(".")
        s = f"{mant}ᴇ{int(exp)}".replace("-", "⁻")
    else:
        s = format(a.normalize(), "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        if s.startswith("0."):
            s = s[1:]
    return ("⁻" if neg else "") + s


def to_display(v):
    if isinstance(v, str):
        return v
    if isinstance(v, Decimal):
        return fmt_num(v)
    if isinstance(v, list) and v and isinstance(v[0], list):
        return "[" + "".join("[" + " ".join(fmt_num(x) for x in r) + "]" for r in v) + "]"
    return "{" + " ".join(fmt_num(x) for x in v) + "}"


# ---------------------------------------------------------------- interpreter

class Calc:
    def __init__(self, src_dir: Path, events=None, trace=False):
        self.src_dir = Path(src_dir)
        self.programs: dict[str, list] = {}
        self.reals: dict[str, Decimal] = {}
        self.strs: dict[str, str] = {}
        self.lists: dict[str, list] = {}
        self.mats: dict[str, list] = {}
        self.events = list(events or [])
        self.screen = [[" "] * COLS for _ in range(ROWS)]
        self.cursor_row = 0
        self.transcript: list[str] = []
        self.trace = trace
        self.steps = 0
        self.max_steps = 20_000_000
        self.depth = 0
        self.warnings: list[str] = []

    # ---- screen
    def clr(self):
        self.screen = [[" "] * COLS for _ in range(ROWS)]
        self.cursor_row = 0

    def screen_text(self):
        return "\n".join("".join(r).rstrip() for r in self.screen)

    def snap(self, why):
        self.transcript.append(f"--- {why}\n{self.screen_text()}")

    def output(self, r, c, s):
        r, c = int(r), int(c)
        if not (1 <= r <= ROWS and 1 <= c <= COLS):
            raise TIError("ERR:DOMAIN Output( position")
        r -= 1
        c -= 1
        if c + len(s) > COLS:
            self.warnings.append(f"Output( wraps past column {COLS}: row {r + 1} col {c + 1} {s!r}")
        for ch in s:
            if r >= ROWS:
                break
            self.screen[r][c] = ch
            c += 1
            if c >= COLS:
                c = 0
                r += 1

    def disp_line(self, text, right=False):
        if self.cursor_row >= ROWS:
            self.screen.pop(0)
            self.screen.append([" "] * COLS)
            self.cursor_row = ROWS - 1
        if len(text) > COLS:
            self.warnings.append(f"Disp text wider than {COLS} columns: {text!r}")
        line = text[:COLS]
        if right:
            line = line.rjust(COLS)
        self.screen[self.cursor_row] = list(line.ljust(COLS))
        self.cursor_row += 1

    # ---- input events
    def next_event(self, kind):
        if not self.events:
            self.snap(f"waiting for {kind} (script ended)")
            raise EndOfScript(kind)
        ev = self.events[0]
        if ev[0] != kind:
            self.snap(f"expected {ev[0]} but program asked for {kind}")
            raise AssertionError(f"script expected {ev!r} but program wants {kind}\n{self.screen_text()}")
        self.events.pop(0)
        return ev[1]

    # ---- programs
    def load(self, name):
        if name not in self.programs:
            path = self.src_dir / f"{name}.tib"
            if not path.exists():
                raise TIError(f"ERR:UNDEFINED prgm{name}")
            self.programs[name] = split_statements(path.read_text(encoding="utf-8"))
        return self.programs[name]

    def run(self, name):
        try:
            self.call(name)
        except StopProgram:
            pass

    def call(self, name):
        stmts = self.load(name)
        self.depth += 1
        if self.depth > 40:
            raise TIError("ERR:MEMORY prgm nesting")
        try:
            self.exec_program(name, stmts)
        except ReturnFromProgram:
            pass
        finally:
            self.depth -= 1

    def exec_program(self, name, stmts):
        pc = 0
        stack = []  # frames: ('if',) ('for', pc, var, end, step) ('while', pc) ('repeat', pc)
        n = len(stmts)
        while pc < n:
            self.steps += 1
            if self.steps > self.max_steps:
                raise TIError("step limit exceeded (infinite loop?)")
            st = stmts[pc]
            head = st[0]
            if self.trace:
                print(name, pc, st)
            if head == ("op", "If "):
                cond = self.truth(self.eval(st[1:]))
                if pc + 1 < n and stmts[pc + 1] == [("op", "Then")]:
                    if cond:
                        stack.append(("if",))
                        pc += 2
                    else:
                        j, kind = self.skip_block(stmts, pc + 2, stop_at_else=True)
                        if kind == "Else":
                            stack.append(("if",))
                        pc = j + 1
                    continue
                pc += 1 if cond else 2
                continue
            if head == ("op", "Then"):
                raise TIError(f"ERR:SYNTAX Then without If in {name}")
            if head == ("op", "Else"):
                if not stack or stack[-1][0] != "if":
                    raise TIError(f"ERR:SYNTAX stray Else in {name}")
                stack.pop()
                j, _ = self.skip_block(stmts, pc + 1, stop_at_else=False)
                pc = j + 1
                continue
            if head == ("op", "End"):
                if not stack:
                    raise TIError(f"ERR:SYNTAX stray End in {name} at {pc}")
                fr = stack[-1]
                if fr[0] == "if":
                    stack.pop()
                    pc += 1
                elif fr[0] == "for":
                    _, top, var, end, step = fr
                    v = self.reals[var] + step
                    self.reals[var] = v
                    if (step > 0 and v <= end) or (step < 0 and v >= end):
                        pc = top + 1
                    else:
                        stack.pop()
                        pc += 1
                elif fr[0] == "while":
                    if self.truth(self.eval(stmts[fr[1]][1:])):
                        pc = fr[1] + 1
                    else:
                        stack.pop()
                        pc += 1
                elif fr[0] == "repeat":
                    if self.truth(self.eval(stmts[fr[1]][1:])):
                        stack.pop()
                        pc += 1
                    else:
                        pc = fr[1] + 1
                continue
            if head == ("op", "For("):
                args = self.split_args(st[1:], closing=True)
                if args[0][0][0] != "var" or len(args[0]) != 1:
                    raise TIError("ERR:SYNTAX For( variable")
                var = args[0][0][1]
                start = self.num(self.eval(args[1]))
                end = self.num(self.eval(args[2]))
                step = self.num(self.eval(args[3])) if len(args) > 3 else D(1)
                self.reals[var] = start
                if (step > 0 and start > end) or (step < 0 and start < end):
                    j, _ = self.skip_block(stmts, pc + 1, stop_at_else=False)
                    pc = j + 1
                else:
                    stack.append(("for", pc, var, end, step))
                    pc += 1
                continue
            if head == ("op", "While "):
                if self.truth(self.eval(st[1:])):
                    stack.append(("while", pc))
                    pc += 1
                else:
                    j, _ = self.skip_block(stmts, pc + 1, stop_at_else=False)
                    pc = j + 1
                continue
            if head == ("op", "Repeat "):
                stack.append(("repeat", pc))
                pc += 1
                continue
            if head == ("op", "Lbl "):
                pc += 1
                continue
            if head == ("op", "Goto "):
                if stack:
                    raise TIError(f"Goto inside an open block in {name} (memory leak on calculator)")
                pc = self.find_label(name, stmts, self.label_of(st[1:]))
                continue
            if head == ("op", "Menu("):
                if stack:
                    raise TIError(f"Menu( inside an open block in {name} (memory leak on calculator)")
                pc = self.do_menu(name, stmts, st[1:])
                continue
            if head == ("op", "Return"):
                raise ReturnFromProgram()
            if head == ("op", "Stop"):
                raise StopProgram()
            if head[0] == "prgm":
                if len(st) != 1:
                    raise TIError("ERR:SYNTAX after prgm")
                self.call(head[1])
                pc += 1
                continue
            self.simple(st)
            pc += 1

    def skip_block(self, stmts, pc, stop_at_else):
        depth = 0
        n = len(stmts)
        while pc < n:
            h = stmts[pc][0]
            if h in (("op", "For("), ("op", "While "), ("op", "Repeat ")):
                depth += 1
            elif h == ("op", "If ") and pc + 1 < n and stmts[pc + 1] == [("op", "Then")]:
                depth += 1
                pc += 1
            elif h == ("op", "If "):
                pc += 1  # single-line If: the next statement belongs to it
                if pc < n and stmts[pc][0] in (("op", "For("), ("op", "While "), ("op", "Repeat ")):
                    depth += 1
            elif h == ("op", "Else") and depth == 0 and stop_at_else:
                return pc, "Else"
            elif h == ("op", "End"):
                if depth == 0:
                    return pc, "End"
                depth -= 1
            pc += 1
        raise TIError("ERR:SYNTAX missing End")

    def label_of(self, toks):
        s = ""
        for t in toks:
            if t[0] == "num":
                s += str(int(t[1])) if t[1] == int(t[1]) else str(t[1])
            elif t[0] == "var":
                s += t[1]
            else:
                raise TIError("ERR:SYNTAX label")
        if not 1 <= len(s) <= 2:
            raise TIError("ERR:SYNTAX label length")
        return s

    def find_label(self, name, stmts, label):
        for i, st in enumerate(stmts):
            if st[0] == ("op", "Lbl ") and self.label_of(st[1:]) == label:
                return i + 1
        raise TIError(f"ERR:LABEL {label} in {name}")

    def do_menu(self, name, stmts, toks):
        args = self.split_args(toks, closing=True)
        title = self.eval(args[0])
        items = []
        for k in range(1, len(args), 2):
            items.append((self.eval(args[k]), self.label_of(args[k + 1])))
        if len(items) > 9:
            raise TIError("Menu( has more than 9 options (Evo limit)")
        for text, label in items:
            if not isinstance(text, str):
                raise TIError("ERR:DATA TYPE Menu( text")
            self.find_label(name, stmts, label)
        self.clr()
        self.output(1, 1, title[:COLS])
        if len(title) > 40:
            self.warnings.append(f"Menu title longer than ~40 characters: {title!r}")
        for k, (text, _) in enumerate(items):
            if len(text) > COLS - 2:
                self.warnings.append(f"Menu item too wide: {text!r}")
            self.output(k + 2, 1, f"{k + 1}:{text}"[:COLS])
        self.snap("Menu")
        choice = self.next_event("menu")
        if not 1 <= choice <= len(items):
            raise AssertionError(f"menu choice {choice} out of range for {title}")
        self.clr()
        return self.find_label(name, stmts, items[choice - 1][1])

    # ---- simple statements
    def simple(self, st):
        head = st[0]
        if head == ("op", "ClrHome"):
            self.clr()
            return
        if head in (("op", "Float"), ("op", "Normal")):
            return
        if head == ("op", "Output("):
            args = self.split_args(st[1:], closing=True)
            r, c, v = (self.eval(a) for a in args)
            self.output(self.num(r), self.num(c), to_display(v))
            return
        if head in (("op", "Disp "), ("op", "Disp")):
            for a in self.split_args(st[1:], closing=False) if len(st) > 1 else []:
                v = self.eval(a)
                if isinstance(v, str):
                    self.disp_line(v)
                else:
                    self.disp_line(to_display(v), right=True)
            return
        if head in (("op", "Pause "), ("op", "Pause")):
            if len(st) > 1:
                v = self.eval(st[1:])
                self.disp_line(to_display(v), right=not isinstance(v, str))
            self.snap("Pause")
            if self.events and self.events[0][0] == "pause":
                self.events.pop(0)
            return
        if head == ("op", "Input "):
            args = self.split_args(st[1:], closing=False)
            prompt = self.eval(args[0])
            target = args[1]
            self.disp_line(prompt)
            self.snap("Input")
            text = self.next_event("input")
            self.screen[self.cursor_row - 1] = list((prompt + text)[:COLS].ljust(COLS))
            if target[0][0] == "strvar":
                self.strs[target[0][1]] = text
            else:
                self.store(self.eval(tokenize_line(text)), target)
            return
        if head == ("op", "DelVar "):
            t = st[1]
            if t[0] == "strvar":
                self.strs.pop(t[1], None)
            elif t[0] == "list":
                self.lists.pop(t[1], None)
            elif t[0] == "mat":
                self.mats.pop(t[1], None)
            elif t[0] == "var":
                self.reals.pop(t[1], None)
            return
        if head == ("op", "Fill("):
            args = self.split_args(st[1:], closing=True)
            v = self.num(self.eval(args[0]))
            t = args[1][0]
            if t[0] == "mat":
                m = self.get_mat(t[1])
                self.mats[t[1]] = [[v] * len(m[0]) for _ in m]
            elif t[0] == "list":
                self.lists[t[1]] = [v] * len(self.get_list(t[1]))
            return
        # expression, optionally stored
        if ("op", "→") in st:
            k = len(st) - 1 - st[::-1].index(("op", "→"))
            val = self.eval(st[:k])
            self.store(val, st[k + 1:])
        else:
            self.eval(st)

    def store(self, val, target):
        t = target[0]
        if t[0] == "var" and len(target) == 1:
            self.reals[t[1]] = self.num(val)
        elif t[0] == "strvar" and len(target) == 1:
            if not isinstance(val, str):
                raise TIError("ERR:DATA TYPE store to Str")
            self.strs[t[1]] = val
        elif t == ("op", "dim("):
            obj = target[1]
            if obj[0] == "list":
                n = int(self.num(val))
                if n < 1 or n > 999:
                    raise TIError("ERR:INVALID DIM list size (Evo rejects empty lists)")
                old = self.lists.get(obj[1], [])
                self.lists[obj[1]] = (old + [D(0)] * n)[:n]
            elif obj[0] == "mat":
                r, c = (int(x) for x in val)
                if not (1 <= r <= 99 and 1 <= c <= 99):
                    raise TIError("ERR:INVALID DIM matrix size")
                old = self.mats.get(obj[1], [])
                new = [[D(0)] * c for _ in range(r)]
                for i in range(min(r, len(old))):
                    for j in range(min(c, len(old[0]))):
                        new[i][j] = old[i][j]
                self.mats[obj[1]] = new
            else:
                raise TIError("ERR:SYNTAX dim store")
        elif t[0] == "list":
            if len(target) == 1:
                if not isinstance(val, list) or not val or isinstance(val[0], list):
                    raise TIError("ERR:DATA TYPE list store")
                self.lists[t[1]] = list(val)
            else:
                idx = int(self.num(self.eval(self.strip_parens(target[1:]))))
                lst = self.get_list(t[1])
                if idx == len(lst) + 1:
                    lst.append(self.num(val))
                elif 1 <= idx <= len(lst):
                    lst[idx - 1] = self.num(val)
                else:
                    raise TIError(f"ERR:INVALID DIM ʟ{t[1]}({idx})")
        elif t[0] == "mat":
            if len(target) == 1:
                if not (isinstance(val, list) and val and isinstance(val[0], list)):
                    raise TIError("ERR:DATA TYPE matrix store")
                self.mats[t[1]] = [list(r) for r in val]
            else:
                args = self.split_args(target[1:], closing=True, opened=True)
                i, j = (int(self.num(self.eval(a))) for a in args)
                m = self.get_mat(t[1])
                if not (1 <= i <= len(m) and 1 <= j <= len(m[0])):
                    raise TIError(f"ERR:INVALID DIM [{t[1]}]({i},{j})")
                m[i - 1][j - 1] = self.num(val)
        else:
            raise TIError(f"ERR:SYNTAX bad store target {target}")

    def strip_parens(self, toks):
        if toks[0] != ("op", "("):
            raise TIError("ERR:SYNTAX index")
        toks = toks[1:]
        if toks and toks[-1] == ("op", ")"):
            toks = toks[:-1]
        return toks

    # ---- helpers
    def num(self, v):
        if not isinstance(v, Decimal):
            raise TIError(f"ERR:DATA TYPE expected number, got {type(v).__name__}")
        return v

    def truth(self, v):
        return self.num(v) != 0

    def get_list(self, name):
        if name not in self.lists:
            raise TIError(f"ERR:UNDEFINED ʟ{name}")
        return self.lists[name]

    def get_mat(self, name):
        if name not in self.mats:
            raise TIError(f"ERR:UNDEFINED [{name}]")
        return self.mats[name]

    def split_args(self, toks, closing, opened=False):
        """Split a comma-separated argument list at depth 0. Drops a final ')'."""
        if opened:
            toks = toks[1:]
        args, cur, depth = [], [], 0
        for t in toks:
            if t[0] == "op" and (t[1].endswith("(") or t[1] == "{"):
                depth += 1
            elif t in (("op", ")"), ("op", "}")):
                depth -= 1
                if depth < 0:
                    if not closing:
                        raise TIError("ERR:SYNTAX unbalanced )")
                    depth = 0
                    continue
            if t == ("op", ",") and depth == 0:
                args.append(cur)
                cur = []
            else:
                cur.append(t)
        args.append(cur)
        return args

    # ---- expression evaluation (precedence climbing)
    def eval(self, toks):
        if not toks:
            raise TIError("ERR:SYNTAX empty expression")
        self._t = list(toks)
        self._i = 0
        v = self.p_or()
        if self._i != len(self._t):
            raise TIError(f"ERR:SYNTAX trailing tokens {self._t[self._i:]}")
        return v

    def peek(self):
        return self._t[self._i] if self._i < len(self._t) else None

    def take(self):
        t = self._t[self._i]
        self._i += 1
        return t

    def p_or(self):
        v = self.p_and()
        while self.peek() in (("op", " or "), ("op", " xor ")):
            op = self.take()[1]
            w = self.p_and()
            a, b = self.truth(v), self.truth(w)
            v = D(int(a or b)) if op == " or " else D(int(a != b))
        return v

    def p_and(self):
        v = self.p_rel()
        while self.peek() == ("op", " and "):
            self.take()
            w = self.p_rel()
            v = D(int(self.truth(v) and self.truth(w)))
        return v

    def p_rel(self):
        v = self.p_add()
        while self.peek() in [("op", o) for o in ("=", "≠", "<", ">", "≤", "≥")]:
            op = self.take()[1]
            w = self.p_add()
            if isinstance(v, str) or isinstance(w, str):
                if op not in ("=", "≠"):
                    raise TIError("ERR:DATA TYPE string compare")
                r = (v == w) if op == "=" else (v != w)
            else:
                a, b = self.num(v), self.num(w)
                r = {"=": a == b, "≠": a != b, "<": a < b, ">": a > b, "≤": a <= b, "≥": a >= b}[op]
            v = D(int(r))
        return v

    def p_add(self):
        v = self.p_mul()
        while self.peek() in (("op", "+"), ("op", "-")):
            op = self.take()[1]
            w = self.p_mul()
            if op == "+" and isinstance(v, str) and isinstance(w, str):
                v = v + w
            else:
                v = self.arith(op, v, w)
        return v

    def starts_primary(self, t):
        if t is None:
            return False
        if t[0] in ("num", "var", "strvar", "list", "mat", "str"):
            return True
        return t[0] == "op" and (t[1] in FUNCS or t[1] in ("(", "{", "getKey"))

    def p_mul(self):
        v = self.p_neg()
        while True:
            t = self.peek()
            if t in (("op", "*"), ("op", "/")):
                self.take()
                w = self.p_neg()
                v = self.arith(t[1], v, w)
            elif self.starts_primary(t):
                w = self.p_neg()
                v = self.arith("*", v, w)
            else:
                return v

    def p_neg(self):
        if self.peek() == ("op", "⁻"):
            self.take()
            v = self.p_neg()
            return self.arith("*", D(-1), v)
        return self.p_pow()

    def p_pow(self):
        v = self.p_primary()
        while True:
            t = self.peek()
            if t == ("op", "^"):
                self.take()
                w = self.p_primary_neg()
                v = self.power(v, w)
            elif t == ("op", "²"):
                self.take()
                v = self.power(v, D(2))
            elif t == ("op", "ᵀ"):
                self.take()
                if not (isinstance(v, list) and v and isinstance(v[0], list)):
                    raise TIError("ERR:DATA TYPE ᵀ")
                v = [list(r) for r in zip(*v)]
            else:
                return v

    def p_primary_neg(self):
        if self.peek() == ("op", "⁻"):
            self.take()
            return self.arith("*", D(-1), self.p_primary())
        return self.p_primary()

    def p_primary(self):
        t = self.take()
        kind, val = t
        if kind == "num":
            return val
        if kind == "str":
            return val
        if kind == "var":
            return self.reals.get(val, D(0))
        if kind == "strvar":
            if val not in self.strs:
                raise TIError(f"ERR:UNDEFINED {val}")
            return self.strs[val]
        if kind == "list":
            lst = self.get_list(val)
            if self.peek() == ("op", "("):
                self.take()
                idx = int(self.num(self.p_or()))
                self.close_paren()
                if not 1 <= idx <= len(lst):
                    raise TIError(f"ERR:INVALID DIM ʟ{val}({idx})")
                return lst[idx - 1]
            return list(lst)
        if kind == "mat":
            m = self.get_mat(val)
            if self.peek() == ("op", "("):
                self.take()
                i = int(self.num(self.p_or()))
                if self.take() != ("op", ","):
                    raise TIError("ERR:SYNTAX matrix index")
                j = int(self.num(self.p_or()))
                self.close_paren()
                if not (1 <= i <= len(m) and 1 <= j <= len(m[0])):
                    raise TIError(f"ERR:INVALID DIM [{val}]({i},{j})")
                return m[i - 1][j - 1]
            return [list(r) for r in m]
        if t == ("op", "("):
            v = self.p_or()
            self.close_paren()
            return v
        if t == ("op", "{"):
            items = [self.num(self.p_or())]
            while self.peek() == ("op", ","):
                self.take()
                items.append(self.num(self.p_or()))
            if self.peek() == ("op", "}"):
                self.take()
            return items
        if t == ("op", "getKey"):
            if self.events and self.events[0][0] == "key":
                self.snap("getKey")
                return D(self.events.pop(0)[1])
            self.snap("getKey")
            if not self.events:
                raise EndOfScript("key")
            raise AssertionError(f"getKey but script has {self.events[0]!r}\n{self.screen_text()}")
        if kind == "op" and val in FUNCS:
            args = [self.p_or()]
            while self.peek() == ("op", ","):
                self.take()
                args.append(self.p_or())
            self.close_paren()
            return self.func(val, args)
        raise TIError(f"ERR:SYNTAX unexpected {t}")

    def close_paren(self):
        t = self.peek()
        if t == ("op", ")"):
            self.take()
        elif t is not None and t not in (("op", ","), ("op", "}")):
            # TI allows omitting ')' only at end of statement or before →
            raise TIError(f"ERR:SYNTAX expected ) got {t}")

    # ---- arithmetic
    def arith(self, op, a, b):
        if isinstance(a, list) or isinstance(b, list):
            return self.arith_agg(op, a, b)
        a, b = self.num(a), self.num(b)
        if op == "+":
            return CTX.add(a, b)
        if op == "-":
            return CTX.subtract(a, b)
        if op == "*":
            return CTX.multiply(a, b)
        if b == 0:
            raise TIError("ERR:DIVIDE BY 0")
        return CTX.divide(a, b)

    def arith_agg(self, op, a, b):
        ismat = lambda x: isinstance(x, list) and x and isinstance(x[0], list)
        if ismat(a) or ismat(b):
            raise TIError("matrix arithmetic is not used by Matrix Evo (exact engine only)")
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                raise TIError("ERR:DIM MISMATCH")
            return [self.arith(op, x, y) for x, y in zip(a, b)]
        if isinstance(a, list):
            return [self.arith(op, x, b) for x in a]
        return [self.arith(op, a, y) for y in b]

    def power(self, a, b):
        a, b = self.num(a), self.num(b)
        if b == int(b):
            r = D(1)
            for _ in range(abs(int(b))):
                r = CTX.multiply(r, a)
            return CTX.divide(D(1), r) if b < 0 else r
        if a < 0:
            raise TIError("ERR:NONREAL ANS")
        return D(math.pow(float(a), float(b)))

    def func(self, name, args):
        n = lambda k: self.num(args[k])
        if name == "abs(":
            return abs(n(0))
        if name == "int(":
            return D(math.floor(n(0)))
        if name == "iPart(":
            return D(int(n(0)))
        if name == "fPart(":
            x = n(0)
            return CTX.subtract(x, D(int(x)))
        if name == "round(":
            places = int(n(1)) if len(args) > 1 else 9
            return CTX.create_decimal(n(0).quantize(Decimal(1).scaleb(-places), rounding="ROUND_HALF_UP")) if n(0) != 0 else D(0)
        if name == "gcd(":
            a, b = n(0), n(1)
            if a != int(a) or b != int(b) or a < 0 or b < 0:
                raise TIError("ERR:DOMAIN gcd(")
            if a >= D("1E12") or b >= D("1E12"):
                raise TIError("gcd( argument above the 1E12 bound Matrix Evo assumes")
            return D(math.gcd(int(a), int(b)))
        if name == "remainder(":
            return D(int(n(0)) % int(n(1)))
        if name == "max(":
            return max(n(0), n(1))
        if name == "min(":
            return min(n(0), n(1))
        if name == "not(":
            return D(int(n(0) == 0))
        if name == "√(":
            if n(0) < 0:
                raise TIError("ERR:NONREAL ANS")
            return CTX.sqrt(n(0))
        if name == "sum(":
            s = D(0)
            for x in args[0]:
                s = CTX.add(s, x)
            return s
        if name == "dim(":
            v = args[0]
            if isinstance(v, list) and v and isinstance(v[0], list):
                return [D(len(v)), D(len(v[0]))]
            if isinstance(v, list):
                return D(len(v))
            raise TIError("ERR:DATA TYPE dim(")
        if name == "length(":
            if not isinstance(args[0], str):
                raise TIError("ERR:DATA TYPE length(")
            return D(len(args[0]))
        if name == "sub(":
            s, a, b = args[0], int(n(1)), int(n(2))
            if not isinstance(s, str) or a < 1 or b < 1 or a + b - 1 > len(s):
                raise TIError("ERR:DOMAIN sub(")
            return s[a - 1:a - 1 + b]
        if name == "inString(":
            s, t = args[0], args[1]
            start = int(n(2)) if len(args) > 2 else 1
            return D(s.find(t, start - 1) + 1)
        if name == "toString(":
            return fmt_num(n(0))
        if name == "expr(":
            if not isinstance(args[0], str):
                raise TIError("ERR:DATA TYPE expr(")
            saved = (self._t, self._i)
            try:
                return self.eval(tokenize_line(args[0]))
            finally:
                self._t, self._i = saved
        if name == "identity(":
            k = int(n(0))
            return [[D(int(i == j)) for j in range(k)] for i in range(k)]
        if name == "augment(":
            a, b = args
            if isinstance(a, list) and a and isinstance(a[0], list):
                if len(a) != len(b):
                    raise TIError("ERR:DIM MISMATCH")
                return [ra + rb for ra, rb in zip(a, b)]
            return list(a) + list(b)
        if name == "rowSwap(":
            m, i, j = [list(r) for r in args[0]], int(n(1)), int(n(2))
            if not (1 <= i <= len(m) and 1 <= j <= len(m)):
                raise TIError("ERR:INVALID DIM rowSwap(")
            m[i - 1], m[j - 1] = m[j - 1], m[i - 1]
            return m
        raise TIError(f"unsupported function {name}")
