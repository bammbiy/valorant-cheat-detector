#!/usr/bin/env python3
"""detection.py 내 탐지 임계값 관련 매직 넘버 탐지.
임계값은 반드시 config.py에서 가져와야 한다."""
import sys
import re
import ast

# detection.py에서만 검사
TARGET = "detection.py"

# 의심 패턴: 0.xx 형태 float 리터럴이 비교 연산에 직접 사용되는 경우
SUSPICIOUS = re.compile(r"(?:>|<|>=|<=|==)\s*0\.\d{2,}")

found = False
for path in sys.argv[1:]:
    if not path.endswith(TARGET):
        continue
    try:
        lines = open(path).readlines()
    except OSError:
        continue
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if SUSPICIOUS.search(stripped):
            print(f"[매직 넘버 의심] {path}:{i} → {stripped}")
            print("  → 임계값은 config.py의 Settings 필드로 정의하세요.")
            found = True

sys.exit(1 if found else 0)
