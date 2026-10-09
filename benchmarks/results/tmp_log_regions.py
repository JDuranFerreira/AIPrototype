"""Append the regions-refactor line to the Vault log (UTF-8, no BOM)."""
from datetime import datetime
from pathlib import Path

LOG = Path(r"C:\AIAccess\Vault\log.md")
text = LOG.read_text(encoding="utf-8")
if not text.endswith("\n"):
    text += "\n"
line = (f"{datetime.now():%Y-%m-%d %H:%M} | structural | aiprototype + agenticos: consumers of the "
        "region refactor updated - AgenticOS backend test_brainlike.py now asserts the six region "
        "names, stats.report_card and source 'language' (full suite 154 passed); Brain map "
        "(BrainMap.tsx, lib/types.ts) rebuilt to show language / knowledge / memory / arithmetic / "
        "prefrontal / monitor plus the report card, English read from language.english, action "
        "selection folded into prefrontal (npm build and 16 frontend tests pass); new Vault report "
        "reports/2026-10-04-regions-refactor.md; HANDOFF updated\n")
LOG.write_text(text + line, encoding="utf-8")
print(LOG.read_text(encoding="utf-8").splitlines()[-1])
