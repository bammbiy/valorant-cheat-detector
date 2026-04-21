#!/usr/bin/env python3
"""
ValoScan 가비지 컬렉션 에이전트

주기적으로 실행해서 코드베이스 품질 문제를 탐지·보고한다.
CI 또는 cron으로 돌리거나 수동으로 실행.

사용법:
    python scripts/gc_agent.py [--fix]

    --fix 플래그: 자동으로 고칠 수 있는 것은 고침 (현재: 미사용 import)
"""
import argparse
import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
TESTS = ROOT / "tests"
SCRIPTS = ROOT / "scripts"

# ── 탐지 규칙 ────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    severity: str   # "error" | "warn" | "info"
    file: str
    line: int
    rule: str
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)

    def add(self, severity: str, file: str, line: int, rule: str, msg: str) -> None:
        self.issues.append(Issue(severity, file, line, rule, msg))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warn"]


def _py_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if ".venv" not in str(p)]


# ── 규칙 1: TODO 주석 탐지 ───────────────────────────────────────────────────

def check_todos(report: Report) -> None:
    pattern = re.compile(r"#\s*TODO", re.IGNORECASE)
    for path in _py_files(ROOT):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.search(line):
                report.add("warn", str(path.relative_to(ROOT)), i,
                           "GC001", f"TODO 주석 발견: {line.strip()}")


# ── 규칙 2: 함수 길이 초과 ───────────────────────────────────────────────────

FUNC_LIMIT = 50

def check_function_lengths(report: Report) -> None:
    for path in _py_files(BACKEND):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > FUNC_LIMIT:
                report.add("warn", str(path.relative_to(ROOT)), node.lineno,
                           "GC002", f"`{node.name}()` {length}줄 — 한계 {FUNC_LIMIT}줄")


# ── 규칙 3: demo_data 직접 import 탐지 ──────────────────────────────────────

DEMO_IMPORT = re.compile(r"from\s+backend\.services\.demo_data\s+import|import\s+backend\.services\.demo_data")
DEMO_ALLOWED = {"backend/services/analyzer.py"}

def check_demo_imports(report: Report) -> None:
    for path in _py_files(BACKEND):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if any(rel.endswith(a) for a in DEMO_ALLOWED):
            continue
        content = path.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if DEMO_IMPORT.search(line):
                report.add("error", rel, i,
                           "GC003", "demo_data 직접 import — analyzer.py 경유 필요")


# ── 규칙 4: naked except 탐지 ────────────────────────────────────────────────

def check_naked_except(report: Report) -> None:
    pattern = re.compile(r"except\s+Exception\s*:")
    for path in _py_files(BACKEND):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if pattern.search(line.strip()) and not line.strip().startswith("#"):
                report.add("warn", str(path.relative_to(ROOT)), i,
                           "GC004", "naked `except Exception` — 구체적 예외 명시 필요")


# ── 규칙 5: 하드코딩 API 키 패턴 탐지 ──────────────────────────────────────

def check_hardcoded_secrets(report: Report) -> None:
    pattern = re.compile(r'RGAPI-[A-Za-z0-9\-]{36}')
    skip = {"demo_data.py", ".env.example"}
    for path in _py_files(ROOT):
        if any(s in str(path) for s in skip):
            continue
        content = path.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                report.add("error", str(path.relative_to(ROOT)), i,
                           "GC005", "하드코딩된 API 키 패턴 감지")


# ── 규칙 6: 미사용 import (ruff 위임) ───────────────────────────────────────

def check_unused_imports(report: Report, fix: bool = False) -> None:
    args = ["ruff", "check", "--select=F401", str(BACKEND)]
    if fix:
        args.append("--fix")
    result = subprocess.run(args, capture_output=True, text=True)
    if result.stdout:
        for line in result.stdout.splitlines():
            report.add("warn", line, 0, "GC006", "미사용 import (ruff F401)")


# ── 규칙 7: 테스트 없는 서비스 파일 ─────────────────────────────────────────

def check_missing_tests(report: Report) -> None:
    service_files = list((BACKEND / "services").glob("*.py"))
    for sf in service_files:
        if sf.name.startswith("_"):
            continue
        test_file = TESTS / f"test_{sf.name}"
        if not test_file.exists():
            report.add("info", str(sf.relative_to(ROOT)), 0,
                       "GC007", f"테스트 파일 없음 → tests/test_{sf.name} 작성 권장")


# ── 출력 ─────────────────────────────────────────────────────────────────────

SEV_ICON = {"error": "✗", "warn": "△", "info": "·"}
SEV_COLOR = {"error": "\033[91m", "warn": "\033[93m", "info": "\033[94m"}
RESET = "\033[0m"

def print_report(report: Report) -> None:
    if not report.issues:
        print(f"\033[92m✓ 가비지 컬렉션 완료 — 문제 없음\033[0m")
        return

    for issue in sorted(report.issues, key=lambda x: (x.severity, x.file)):
        icon = SEV_ICON.get(issue.severity, "?")
        color = SEV_COLOR.get(issue.severity, "")
        loc = f"{issue.file}:{issue.line}" if issue.line else issue.file
        print(f"{color}{icon} [{issue.rule}] {loc}{RESET}")
        print(f"    {issue.message}")

    errors = len(report.errors)
    warnings = len(report.warnings)
    print(f"\n{'─' * 50}")
    print(f"errors: {errors}  warnings: {warnings}  total: {len(report.issues)}")

    if errors:
        print("\033[91m커밋 전 error를 모두 해결하세요.\033[0m")


def main() -> int:
    parser = argparse.ArgumentParser(description="ValoScan GC Agent")
    parser.add_argument("--fix", action="store_true", help="자동 수정 가능한 항목 수정")
    args = parser.parse_args()

    report = Report()
    check_todos(report)
    check_function_lengths(report)
    check_demo_imports(report)
    check_naked_except(report)
    check_hardcoded_secrets(report)
    check_unused_imports(report, fix=args.fix)
    check_missing_tests(report)

    print_report(report)
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
