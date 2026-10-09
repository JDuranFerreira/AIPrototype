"""ASDiv problems by school grade: the outside exam for each level of the world-based school.

ASDiv (Miao et al. 2020) labels each problem with a grade (1-6). Grade 1 is the outside check for P1,
grade 2 for P2. Answers like "9 (apples)" become 9; answers that aren't one number (times like 3:30,
several numbers) are left out.
"""
import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_asdiv(grade):
    rows = []
    for p in ET.parse(HERE / "asdiv.xml").getroot().iter("Problem"):
        if p.get("Grade") != str(grade):
            continue
        ans = (p.findtext("Answer") or "").split("(")[0].strip()
        if not re.fullmatch(r"-?\d+(\.\d+)?(/\d+)?", ans):
            continue
        body, question = (p.findtext("Body") or "").strip(), (p.findtext("Question") or "").strip()
        rows.append({"id": p.get("ID"), "text": f"{body} {question}", "answer": Fraction(ans),
                     "type": p.findtext("Solution-Type"), "formula": p.findtext("Formula")})
    return rows
