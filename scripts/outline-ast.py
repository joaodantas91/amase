#!/usr/bin/env python3
"""
Compact AST / symbol outline extractor (token-diet code map).

Prints classes, functions, methods, interfaces, types and exported symbols for a
file or directory without dumping full source. Pure Python standard library: no
third-party runtime required.

Usage:
    scripts/outline-ast.py <file-or-dir> [--max-depth N] [--include-empty]

Why: an agent reading 10 full files burns ~80% more tokens than reading one
compact symbol map. See docs/OPEN_SOURCE_TOOL_REGISTRY.md.
"""
import argparse
import ast
import os
import re
import sys

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build",
    "out", "target", "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
    ".worktrees", "coverage", ".next", ".nuxt", ".cache", "vendor", "skills",
    ".agents", "repos",
}

SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".pdf", ".zip",
    ".gz", ".tar", ".br", ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mp3",
    ".lock", ".map", ".min.js", ".min.css",
}

MAX_BYTES = 2 * 1024 * 1024

LANG_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "js",
    ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts",
    ".go": "go",
    ".rs": "rust",
    ".java": "clike", ".kt": "clike", ".kts": "clike", ".scala": "clike",
    ".cs": "clike", ".swift": "clike", ".c": "clike", ".h": "clike",
    ".cc": "clike", ".cpp": "clike", ".cxx": "clike", ".hpp": "clike",
    ".m": "clike", ".mm": "clike", ".php": "clike", ".rb": "clike",
    ".sh": "clike", ".bash": "clike",
}

# --------------------------------------------------------------------------
# Python: precise via the stdlib ast module.
# --------------------------------------------------------------------------
def _py_args(node):
    try:
        return ast.unparse(node.args)
    except Exception:
        return "..."


def _py_returns(node):
    if getattr(node, "returns", None) is None:
        return ""
    try:
        return " -> " + ast.unparse(node.returns)
    except Exception:
        return ""


def outline_python(src):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []

    out = []

    def walk(body, depth, in_class=False):
        for node in body:
            pad = "  " * depth
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                out.append(
                    f"{pad}{kind} {node.name}({_py_args(node)}){_py_returns(node)}"
                    f"  L{node.lineno}"
                )
            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                head = f"class {node.name}" + (f"({', '.join(bases)})" if bases else "")
                out.append(f"{pad}{head}  L{node.lineno}")
                walk(node.body, depth + 1, True)
            elif not in_class and isinstance(node, (ast.Assign, ast.AnnAssign)):
                names = []
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name) and t.id.isupper():
                        names.append(t.id)
                if names:
                    out.append(f"{pad}{', '.join(names)}  L{node.lineno}")
        return out

    return walk(tree.body, 0)


# --------------------------------------------------------------------------
# JS / TS: line-oriented declaration scan with brace-depth indentation.
# --------------------------------------------------------------------------
_RE_JS_CLASS = re.compile(
    r"\b(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+(\w+)"
    r"(?:\s+extends\s+([\w.]+))?"
)
_RE_JS_FUNC = re.compile(
    r"\b(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*(\w+)\s*\("
)
_RE_JS_ARROW = re.compile(
    r"\b(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::[^=]+)?=\s*"
    r"(?:async\s*)?(?:\([^)]*\)|\w+)\s*(?::[^=]+)?=>"
)
_RE_JS_IFACE = re.compile(r"\b(?:export\s+(?:default\s+)?)?(?:interface|type)\s+(\w+)")
_RE_JS_ENUM = re.compile(r"\b(?:export\s+(?:default\s+)?)?(?:enum|namespace|module)\s+(\w+)")
_RE_JS_METHOD = re.compile(
    r"^\s*(?:(?:public|private|protected|static|async|readonly|override|abstract)\s+)*"
    r"(?:get\s+|set\s+)?#?(\w+)\s*\([^;{}]*\)\s*(?::\s*[\w<>\[\]|,. ]+)?\s*\{\s*$"
)
_JS_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "return", "function", "else",
    "do", "try", "with", "new", "typeof", "delete", "await", "yield",
}
_RE_BRACE_STRIP = re.compile(r"""(['"`])(?:\\.|(?!\1).)*\1|//.*$""")


def _brace_delta(line):
    clean = _RE_BRACE_STRIP.sub("", line)
    return clean.count("{") - clean.count("}")


def outline_js(src):
    out = []
    depth = 0
    for lineno, line in enumerate(src.splitlines(), 1):
        stripped = line.strip()
        pad = "  " * min(depth, 16)
        m = _RE_JS_CLASS.search(line)
        if m:
            ext = f" extends {m.group(2)}" if m.group(2) else ""
            out.append(f"{pad}class {m.group(1)}{ext}  L{lineno}")
        elif (m := _RE_JS_FUNC.search(line)):
            out.append(f"{pad}function {m.group(1)}()  L{lineno}")
        elif (m := _RE_JS_IFACE.search(line)):
            out.append(f"{pad}type {m.group(1)}  L{lineno}")
        elif (m := _RE_JS_ENUM.search(line)):
            out.append(f"{pad}enum {m.group(1)}  L{lineno}")
        elif (m := _RE_JS_ARROW.search(line)):
            out.append(f"{pad}const {m.group(1)} = fn  L{lineno}")
        elif (m := _RE_JS_METHOD.match(line)):
            name = m.group(1)
            if name not in _JS_KEYWORDS:
                out.append(f"{pad}{name}()  L{lineno}")
        depth = max(0, depth + _brace_delta(line))
    return out


# --------------------------------------------------------------------------
# Go
# --------------------------------------------------------------------------
_RE_GO_FUNC = re.compile(r"^func\s+(?:\([^)]*\)\s+)?(\w+)\s*[\(\[]")
_RE_GO_TYPE = re.compile(r"^type\s+(\w+)\s+(struct|interface|func|map|\[|string|int|bool|float)")


def outline_go(src):
    out = []
    for lineno, line in enumerate(src.splitlines(), 1):
        m = _RE_GO_FUNC.match(line)
        if m:
            out.append(f"func {m.group(1)}()  L{lineno}")
            continue
        m = _RE_GO_TYPE.match(line)
        if m:
            out.append(f"type {m.group(1)} {m.group(2)}  L{lineno}")
    return out


# --------------------------------------------------------------------------
# Rust
# --------------------------------------------------------------------------
_RE_RS_FN = re.compile(r"^\s*(pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:const\s+)?fn\s+(\w+)")
_RE_RS_TYPE = re.compile(r"^\s*(pub(?:\([^)]*\))?\s+)?(struct|enum|trait|mod|type|union)\s+(\w+)")
_RE_RS_IMPL = re.compile(r"^\s*impl(?:<[^>]*>)?\s+(?:[\w:<>']+\s+for\s+)?([\w:<>']+)")


def outline_rust(src):
    out = []
    for lineno, line in enumerate(src.splitlines(), 1):
        m = _RE_RS_FN.match(line)
        if m:
            out.append(f"fn {m.group(2)}()  L{lineno}")
            continue
        m = _RE_RS_TYPE.match(line)
        if m:
            out.append(f"{m.group(2)} {m.group(3)}  L{lineno}")
            continue
        m = _RE_RS_IMPL.match(line)
        if m:
            out.append(f"impl {m.group(1)}  L{lineno}")
    return out


# --------------------------------------------------------------------------
# Generic C-like (Java, Kotlin, C#, C/C++, Swift, PHP, Ruby, shell).
# --------------------------------------------------------------------------
_RE_CLIKE_TYPE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|abstract|final|static|sealed|open|data|partial)\s+)*"
    r"(class|interface|enum|struct|record|trait|object|protocol|union)\s+(\w+)"
)
_RE_CLIKE_FUNC = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|final|abstract|override|virtual|"
    r"async|suspending|inline|extern|const|unsigned|signed|explicit|friend|export)\s+)*"
    r"(?:def\s+)?(?:[\w:<>\[\],.?&*]+[\s*&]+)+(\w+)\s*\([^;]*\)\s*(?:const\s*)?(?:\{|=>|throws|;)"
)
_RE_SHELL_FUNC = re.compile(r"^\s*(?:function\s+)?([\w.-]+)\s*\(\s*\)\s*\{")


def outline_clike(src, ext):
    out = []
    for lineno, line in enumerate(src.splitlines(), 1):
        if ext in (".sh", ".bash"):
            m = _RE_SHELL_FUNC.match(line)
            if m:
                out.append(f"fn {m.group(1)}  L{lineno}")
            continue
        m = _RE_CLIKE_TYPE.match(line)
        if m:
            out.append(f"{m.group(1)} {m.group(2)}  L{lineno}")
            continue
        m = _RE_CLIKE_FUNC.match(line)
        if m:
            name = m.group(1)
            if name not in ("if", "for", "while", "switch", "catch", "return", "sizeof"):
                out.append(f"{name}()  L{lineno}")
    return out


PARSERS = {
    "python": outline_python,
    "js": outline_js,
    "ts": outline_js,
    "go": outline_go,
    "rust": outline_rust,
}


def outline_source(path, src):
    ext = os.path.splitext(path)[1].lower()
    lang = LANG_BY_EXT.get(ext)
    if lang is None:
        return []
    if lang == "clike":
        return outline_clike(src, ext)
    parser = PARSERS[lang]
    if parser is outline_js:
        return outline_js(src)
    return parser(src)


def iter_files(target, max_depth):
    if os.path.isfile(target):
        yield target
        return
    root_depth = target.rstrip(os.sep).count(os.sep)
    for dirpath, dirnames, filenames in os.walk(target):
        depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        )
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1].lower()
            if ext in SKIP_EXTS:
                continue
            if ext not in LANG_BY_EXT:
                continue
            yield os.path.join(dirpath, name)


def outline_file(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
    except OSError:
        return None
    symbols = outline_source(path, src)
    if not symbols:
        return None
    return os.path.relpath(path), len(src.splitlines()), symbols


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print a compact AST/symbol outline for files or directories.",
    )
    parser.add_argument("target", help="File or directory to outline")
    parser.add_argument("--max-depth", type=int, default=None,
                        help="Maximum directory recursion depth")
    parser.add_argument("--include-empty", action="store_true",
                        help="Also list files that yield no symbols")
    parser.add_argument("--include-symbols-only", action="store_true",
                        help="Output only function signatures and interface contracts (minified skeleton)")
    args = parser.parse_args(argv)

    if not os.path.exists(args.target):
        sys.stderr.write(f"outline-ast: no such file or directory: {args.target}\n")
        return 1

    files = 0
    symbols = 0
    for path in iter_files(args.target, args.max_depth):
        result = outline_file(path)
        if result is None:
            if args.include_empty and os.path.isfile(path):
                print(f"{os.path.relpath(path)}: (no symbols)")
            continue
        rel, nlines, syms = result
        files += 1
        symbols += len(syms)
        if args.include_symbols_only:
            for line in syms:
                m = re.match(r'(.+)  L(\d+)$', line)
                if m:
                    print(f"{rel}: {m.group(1)} (L{m.group(2)})")
                else:
                    print(f"{rel}: {line}")
        else:
            print(f"{rel}: {nlines} lines")
            for line in syms:
                print(f"  {line}")
    if files == 0:
        sys.stderr.write("outline-ast: no supported source files found\n")
        return 1
    if args.include_symbols_only:
        print(f"# {symbols} symbols")
    else:
        print(f"# {files} files, {symbols} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(main())
