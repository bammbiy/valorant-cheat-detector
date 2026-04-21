#!/usr/bin/env python3
"""커밋 전 TODO 주석 탐지. 발견 시 커밋 차단."""
import sys
import re

TODO_PATTERN = re.compile(r"#\s*TODO", re.IGNORECASE)
found = False

for path in sys.argv[1:]:
    try:
        lines = open(path).readlines()
    except OSError:
        continue
    for i, line in enumerate(lines, 1):
        if TODO_PATTERN.search(line):
            print(f"[TODO 차단] {path}:{i} → {line.rstrip()}")
            print("  → 이슈로 올리거나 구현 후 커밋하세요.")
            found = True

sys.exit(1 if found else 0)
