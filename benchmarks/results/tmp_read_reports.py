"""Read the REPORT line out of the real-brain level logs (PowerShell wrote them as UTF-16)."""
import json
import re

for lv in ("P1", "P2", "P3", "P4"):
    raw = open(f"benchmarks/results/real_brain_school_{lv}_reteach.txt", "rb").read()
    text = None
    for enc in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    m = re.search(r"REPORT (\{.*\})", text)
    e = json.loads(m.group(1)) if m else {}
    print(lv, "score", e.get("score"), e.get("grade"),
          "readiness", e.get("readiness"),
          "| strengths:", e.get("strengths"))
    print("   work_on:", e.get("work_on"))
