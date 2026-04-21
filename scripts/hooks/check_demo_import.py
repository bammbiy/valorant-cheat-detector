#!/usr/bin/env python3
"""routes.py 등에서 demo_data를 직접 import하면 커밋 차단.
demo_data는 반드시 analyzer.py를 통해서만 접근해야 한다."""
import sys
import re

PATTERN = re.compile(r"from\s+backend\.services\.demo_data\s+import|import\s+backend\.services\.demo_data")
ALLOWED = {"backend/services/analyzer.py"}

found = False
for path in sys.argv[1:]:
    # analyzer.py는 허용
    normalized = path.replace("\\", "/")
    if any(normalized.endswith(a) for a in ALLOWED):
        continue
    try:
        content = open(path).read()
    except OSError:
        continue
    if PATTERN.search(content):
        print(f"[demo_data 직접 import 차단] {path}")
        print("  → demo_data는 analyzer.py를 통해서만 접근하세요.")
        found = True

sys.exit(1 if found else 0)
