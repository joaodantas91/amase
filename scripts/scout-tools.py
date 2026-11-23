#!/usr/bin/env python3
"""Scout open-source token-reduction tools: availability + outline benchmark."""
import argparse
import json
import os
import shutil
import subprocess
import sys

TOOLS = [
    ("tree-sitter", ["tree-sitter", "--version"], "AST outline"),
    ("ctags", ["ctags", "--version"], "AST outline"),
    ("ast-grep", ["sg", "--version"], "AST search"),
    ("repomix", ["npx", "repomix", "--version"], "Token-minified packing"),
    ("code2prompt", ["code2prompt", "--version"], "Context packing"),
    ("files-to-prompt", ["files-to-prompt", "--version"], "Context packing"),
    ("tiktoken", ["python3", "-c", "import tiktoken; print(tiktoken.__version__)"], "Token accounting"),
]


def check_tools():
    rows = []
    for name, cmd, category in TOOLS:
        exe = cmd[0]
        installed = shutil.which(exe) is not None
        version = ""
        if installed:
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                version = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else "installed"
            except Exception:
                version = "installed"
        rows.append({"name": name, "category": category, "installed": installed, "version": version})
    return rows


def estimate_tokens(text):
    return max(1, len(text) // 4)


def benchmark(target):
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outline-ast.py")
    if not os.path.exists(script):
        raise FileNotFoundError(script)
    if os.path.isfile(target):
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            baseline_text = f.read()
    else:
        baseline_text = ""
        for root, _, files in os.walk(target):
            for name in files:
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        baseline_text += f.read()
                except OSError:
                    continue
    proc = subprocess.run([sys.executable, script, target], capture_output=True, text=True)
    outline_text = proc.stdout
    base_tokens = estimate_tokens(baseline_text)
    outline_tokens = estimate_tokens(outline_text)
    reduction = 100.0 * (base_tokens - outline_tokens) / base_tokens
    return {
        "target": target,
        "baseline_tokens": base_tokens,
        "outline_tokens": outline_tokens,
        "reduction_percent": round(reduction, 2),
        "pass_40_percent": reduction >= 40.0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Scout token-reduction tools and benchmark AST outlines.")
    parser.add_argument("--benchmark", metavar="PATH", help="Benchmark outline-ast.py against a file or directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    if args.benchmark:
        result = benchmark(args.benchmark)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"target: {result['target']}")
            print(f"baseline tokens: {result['baseline_tokens']}")
            print(f"outline tokens:  {result['outline_tokens']}")
            print(f"reduction:       {result['reduction_percent']}%")
            print(f"pass >=40%:      {result['pass_40_percent']}")
        return 0 if result["pass_40_percent"] else 1

    rows = check_tools()
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    print(f"{'tool':16} {'installed':10} {'category':24} version")
    for row in rows:
        print(f"{row['name']:16} {str(row['installed']):10} {row['category']:24} {row['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
