#!/usr/bin/env python3
"""함수/메서드 길이가 50줄을 초과하면 커밋 차단."""
import sys
import ast

LIMIT = 50
found = False

for path in sys.argv[1:]:
    try:
        source = open(path).read()
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        continue

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        start = node.lineno
        end = node.end_lineno or start
        length = end - start + 1
        if length > LIMIT:
            print(f"[함수 길이 초과] {path}:{start} `{node.name}()` — {length}줄 (최대 {LIMIT}줄)")
            print(f"  → 역할별로 함수를 분리하세요.")
            found = True

sys.exit(1 if found else 0)
