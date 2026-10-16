"""Kindergarten exam against a chosen brain_state directory (read-only)."""
import sys
from pathlib import Path

HERE = Path(r"C:\AIAccess\Projects\AIPrototype")
sys.path.insert(0, str(HERE))
from brainlike.regions import Mind                       # noqa: E402
from brainlike.serve import handle_kindergarten          # noqa: E402

state = sys.argv[1] if len(sys.argv) > 1 else "brain_state"
mind = Mind.load(HERE / state)
r = handle_kindergarten(mind, "kindergarten", {"lesson": "exam"})
e = r["kindergarten_exam"]
print(f"{state}: kindergarten {e['right']}/{e['of']}")
