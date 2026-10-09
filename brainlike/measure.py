"""Measurement: converting amounts with units, using what the knowledge region knows.

  "A trip takes 2 hours and 15 minutes. How many minutes is that?"
      -> amounts: 2 hour + 15 minute; the question asks for minutes
      -> the knowledge region knows "minutes in an hour = 60"
      -> 2*60+15
If the fact isn't known, it says which fact it needs ("minutes in an hour").

Recognising the unit words (hours, hrs, h ...) is perception; the conversion
facts are knowledge that has to be taught.
"""
import re

UNITS = {
    "dollar": ["dollars", "dollar", "$"], "cent": ["cents", "cent", "c"],
    "hour": ["hours", "hour", "hrs", "hr", "h"], "minute": ["minutes", "minute", "mins", "min"],
    "second": ["seconds", "second", "secs", "sec", "s"],
    "kilogram": ["kilograms", "kilogram", "kg"], "gram": ["grams", "gram", "g"],
    "litre": ["litres", "litre", "liters", "liter", "l"], "millilitre": ["millilitres", "millilitre", "milliliters", "milliliter", "ml"],
    "km": ["kilometres", "kilometre", "kilometers", "kilometer", "km"], "metre": ["metres", "metre", "meters", "meter", "m"],
    "centimetre": ["centimetres", "centimetre", "centimeters", "centimeter", "cm"],
}
# big unit -> (small unit, the knowledge question that holds how many small units make one big unit)
CONVERSIONS = {
    "dollar": ("cent", "cents in a dollar"), "hour": ("minute", "minutes in an hour"),
    "minute": ("second", "seconds in a minute"), "kilogram": ("gram", "g in a kilogram"),
    "litre": ("millilitre", "ml in a litre"), "km": ("metre", "m in a km"), "metre": ("centimetre", "cm in a metre"),
}
_WORD_TO_UNIT = {w: u for u, ws in UNITS.items() for w in ws}
_UNIT_WORDS = "|".join(sorted((re.escape(w) for w in _WORD_TO_UNIT), key=len, reverse=True))
_AMOUNT = re.compile(rf"(\d+(?:\.\d+)?)\s*({_UNIT_WORDS})\b", re.I)


def unit(word):
    return _WORD_TO_UNIT.get(word.lower())


def read(text, known):
    """-> {"say": expression} | {"need": fact question} | None if this isn't a unit conversion."""
    t = text.lower()
    m = re.search(rf"(?:how many|in)\s+({_UNIT_WORDS})\b(?![^.?!]*\b(?:left|more|less|change|altogether|each)\b)", t)
    if not m:
        return None
    target = unit(m.group(1))
    story = t[:m.start()]
    if re.search(r"\bhalf an hour\b", story) and target == "minute":
        return {"need": "minutes in half an hour"} if "minutes in half an hour" not in known else \
            {"say": f"{known['minutes in half an hour']}*1"}
    amounts = [(float(n), unit(u)) for n, u in _AMOUNT.findall(story)]
    if not amounts or len(amounts) > 2:
        return None
    parts = []
    for value, u in amounts:
        if u == target:
            parts.append(f"{value:g}")
            continue
        conv = CONVERSIONS.get(u)
        if not conv or conv[0] != target:
            return None                                  # not a one-step conversion it knows how to do
        if conv[1] not in known:
            return {"need": conv[1]}
        parts.append(f"{value:g}*{known[conv[1]]}")
    if len(parts) == 1 and amounts[0][1] == target:
        return None                                      # nothing to convert
    return {"say": "+".join(parts)}
