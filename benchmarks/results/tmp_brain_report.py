"""Print a compact efficiency + regions summary of the real brain from the serve stats JSON."""
import json
import os

d = json.load(open(os.path.join(os.environ["TEMP"], "stats.json"), encoding="utf-8-sig"))
print("total_weights", d["total_weights"], "active_weights", d["active_weights"],
      "active%", round(100 * d["active_weights"] / d["total_weights"], 1))
print("basic_known", d["basic_known"], "of", d["total_problems"],
      "big_known", d["big_known"], "free_known", d["free_known"],
      "rules_known", d["rules_known"], "phrases_known", d["phrases_known"])
print("usage", d["usage"])
print()
for r in d["regions"]:
    print("==", r["name"])
    for k, v in r.items():
        if k in ("name", "what"):
            continue
        if isinstance(v, (dict, list)):
            print("   ", k, "=", json.dumps(v, ensure_ascii=False)[:600])
        else:
            print("   ", k, "=", v)
