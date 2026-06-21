# File: utils/report_patcher.py
"""Pytest-HTML report patcher.

Fixes SecurityError: history.pushState on file:// protocol.
Wraps pushState call in try/catch so the JS init doesn't crash,
allowing the test results table to render.

Usage:
    python utils/report_patcher.py reports/report.html
"""

from __future__ import annotations

import sys
from pathlib import Path


def patch_report(report_path: str | Path) -> bool:
    path = Path(report_path)
    if not path.exists():
        print(f'[ERROR] File not found: {path}')
        return False

    content = path.read_text(encoding='utf-8')

    if 'try{window.history.pushState(' in content:
        print('[SKIP] Already patched')
        return True

    old = 'window.history.pushState({}, null, unescape(url.href))'
    new = 'try{window.history.pushState({}, null, unescape(url.href))}catch(e){}'

    if old not in content:
        print('[WARN] pushState pattern not found')
        return False

    content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')
    print(f'[OK] Patched: {path}')
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        target = (
            Path(__file__).resolve().parent.parent
            / 'reports' / 'report.html'
        )
    else:
        target = sys.argv[1]

    ok = patch_report(target)
    sys.exit(0 if ok else 1)
