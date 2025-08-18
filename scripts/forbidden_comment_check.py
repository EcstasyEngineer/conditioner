#!/usr/bin/env python3
"""
Fail the build if any forbidden keywords appear inside code comments.

- Scans common source files recursively from repo root.
- Supports single-line and block comments for several languages.
- Prints all violations with file, line, and a short excerpt, then exits 1.

Forbidden keywords are drawn from the screenshots and include both lists:
  1) TODO, workaround, simulate, for now, in the future, actual implementation, temporary,
     hack, FIXME, placeholder, mock implementation, stub, dummy, fake implementation,
     eventually, later, quick fix, band-aid, kludge, interim solution
  2) FIXED, CORRECTED, FIX, FIXES, NEW, CHANGED, CHANGES, CHANGE, MODIFY, UPDATE

Notes:
- Matching is case-insensitive.
- Matches only within comments; code identifiers are ignored.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, Iterator, Tuple

# Root of the repository (current working directory in CI)
REPO_ROOT = Path(__file__).resolve().parents[1]

# File globs/extensions to scan
EXTENSIONS = {
    # Python
    ".py": "py",
    # JavaScript/TypeScript
    ".js": "js",
    ".ts": "js",
    ".jsx": "js",
    ".tsx": "js",
    # JSON, YAML (no comments in JSON, but some repos allow // in .jsonc; we skip .json)
    ".jsonc": "js",
    ".yaml": "yaml",
    ".yml": "yaml",
    # Markdown (treat HTML comments)
    ".md": "md",
    # Shell / Batch
    ".sh": "shell",
    ".bat": "batch",
    ".cmd": "batch",
    # Others you might add later (rs, go, java, css, html)
    ".rs": "cstyle",
    ".go": "cstyle",
    ".java": "cstyle",
    ".c": "cstyle",
    ".h": "cstyle",
    ".cpp": "cstyle",
    ".hpp": "cstyle",
    ".css": "css",
    ".html": "html",
}

# Forbidden phrases (case-insensitive); keep longest first to avoid partial masking in excerpts
FORBIDDEN = [
    # Screenshot 1 (blacklist)
    "interim solution",
    "fake implementation",
    "mock implementation",
    "actual implementation",
    "quick fix",
    "for now",
    "in the future",
    "band-aid",
    "placeholder",
    "workaround",
    "temporary",
    "kludge",
    "eventually",
    "later",
    "simulate",
    "FIXME",
    "dummy",
    "stub",
    "TODO",
    # Screenshot 2 (strictly forbidden)
    "CORRECTED",
    "CHANGES",
    "CHANGE",
    "CHANGED",
    "FIXES",
    "FIXED",
    "MODIFY",
    "UPDATE",
    "FIX",
    "NEW",
]

# Precompile a case-insensitive regex that matches any forbidden phrase as a whole word-ish sequence
# Use word boundaries where reasonable; for multi-word phrases, just search the phrase.
PHRASE_REGEXES = [
    re.compile(r"(?i)\b" + re.escape(p) + r"\b") if " " not in p else re.compile(r"(?i)" + re.escape(p))
    for p in FORBIDDEN
]

# Comment extractors by language kind
# Each extractor yields (line_number, comment_text)

def extract_py(path: Path) -> Iterator[Tuple[int, str]]:
    # Only handle # comments; ignore triple-quoted strings to keep it simple
    with path.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if "#" in line:
                idx = line.find("#")
                yield i, line[idx+1:]

def extract_js(path: Path) -> Iterator[Tuple[int, str]]:
    # // line and /* block */ comments
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Line comments
    for i, line in enumerate(text.splitlines(), 1):
        m = re.search(r"//(.*)", line)
        if m:
            yield i, m.group(1)
    # Block comments
    for m in re.finditer(r"/\*(.*?)\*/", text, flags=re.S):
        start_offset = m.start()
        start_line = text[:start_offset].count("\n") + 1
        yield start_line, m.group(1)

def extract_cstyle(path: Path) -> Iterator[Tuple[int, str]]:
    return extract_js(path)

def extract_yaml(path: Path) -> Iterator[Tuple[int, str]]:
    with path.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            s = line.lstrip()
            if s.startswith("#"):
                yield i, s[1:]

def extract_md(path: Path) -> Iterator[Tuple[int, str]]:
    # HTML comments in Markdown: <!-- ... -->
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"<!--(.*?)-->", text, flags=re.S):
        start_line = text[:m.start()].count("\n") + 1
        yield start_line, m.group(1)

def extract_shell(path: Path) -> Iterator[Tuple[int, str]]:
    with path.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            if "#" in line:
                idx = line.find("#")
                yield i, line[idx+1:]

def extract_batch(path: Path) -> Iterator[Tuple[int, str]]:
    with path.open(encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            s = line.lstrip()
            if s.startswith("REM ") or s.startswith("rem ") or s.startswith("::"):
                yield i, s

def extract_css(path: Path) -> Iterator[Tuple[int, str]]:
    return extract_js(path)

def extract_html(path: Path) -> Iterator[Tuple[int, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"<!--(.*?)-->", text, flags=re.S):
        start_line = text[:m.start()].count("\n") + 1
        yield start_line, m.group(1)

EXTRACTORS = {
    "py": extract_py,
    "js": extract_js,
    "yaml": extract_yaml,
    "md": extract_md,
    "shell": extract_shell,
    "batch": extract_batch,
    "cstyle": extract_cstyle,
    "css": extract_css,
    "html": extract_html,
}

SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "dist", "build", ".mypy_cache", ".pytest_cache"}


def iter_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # prune skip dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            p = Path(dirpath) / name
            ext = p.suffix.lower()
            if ext in EXTENSIONS:
                yield p


def find_violations(path: Path) -> Iterator[Tuple[int, str, str]]:
    kind = EXTENSIONS.get(path.suffix.lower())
    if not kind:
        return
    extractor = EXTRACTORS.get(kind)
    if not extractor:
        return
    for line_no, comment in extractor(path):
        lower = comment.lower()
        for phrase, rx in zip(FORBIDDEN, PHRASE_REGEXES):
            if rx.search(comment):
                # Create a short excerpt
                excerpt = comment.strip().replace("\n", " ")
                if len(excerpt) > 120:
                    excerpt = excerpt[:117] + "..."
                yield line_no, phrase, excerpt


def main() -> int:
    root = REPO_ROOT
    any_fail = False
    for p in iter_files(root):
        for line_no, phrase, excerpt in find_violations(p):
            any_fail = True
            rel = p.relative_to(root)
            print(f"ERROR: {rel}:{line_no}: forbidden comment term '{phrase}' found: {excerpt}")
    if any_fail:
        print("\nComments containing these terms are forbidden. Please remove or reword them.")
        return 1
    print("No forbidden comment terms found.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
