"""Reading the request in a question: what kind of answer it wants, and about what.

This is the first thing to do with any question, and it is deliberately small and separate: a child does
not start working out "how many cars do they need?" - it reads that the answer is a number of CARS (not
of people), and that it has to be a whole number of trips. A taught recipe then says which request it
answers, so it never answers a question it was not taught to answer. No imports: everything here is
language, nothing else.
"""
import re

_ASKS = (
    ("needed", r"\b(?:how many|how much)\b[^.?]*?\b(?:are|is|do|does|did|will|can|should)\b[^.?]*?\b(?:need|needs|needed|require|required)\b"
               r"|\benough\b[^.?]*?\bfor\b"),
    ("each", r"\b(?:how many|how much)\b[^.?]*?\b(?:in|per)\s+(?:each|one)\b"
             r"|\bhow many\b[^.?]*?\beach\b[^.?]*?\b(?:get|gets|have|has|receive|receives|need|needs|are|is)\b"
             r"|\bper\s+(?:child|person|kid|friend|head|group|box|bag|table|car|bus|boat|tent)\b"),
    ("all", r"\b(?:in all|altogether|in total|all together)\b"
            r"|\bhow many\b[^.?]*?\b(?:are there|were there)\b"),
    ("money", r"\bhow much money\b|\bhow much\b[^.?]*?\b(?:money|dollars?|cents?|pounds?)\b"
              r"|\bhow much\b[^.?]*?\bcost\b"),
    ("left", r"\bhow many\b[^.?]*?\b(?:left|remain|remains|now)\b"),
)
_ASK_THING = re.compile(r"\b(?:how many|how much|how long|what time|which)\b(?:\s+(\w+))?(?:\s+(\w+))?", re.I)
_ASK_PHRASE = re.compile(r"\b(?:how many|how much)\s+((?:[a-z]+\s+){1,4}?)(?=(?:are|is|do|does|did|has|have|had|can|"
                          r"will|would|cost|\?|$))", re.I)
_NOTHING = {"many", "much", "more", "less", "is", "are", "was", "were", "does", "do", "did", "the", "a", "an",
            "long", "time", "number", "of", "in", "on", "at", "now", "left", "and", "or", "that", "this", "it",
            "each", "per", "will", "would", "can", "could", "have", "has", "had", "get", "got", "there", "they",
            "them", "we", "you", "he", "she", "i", "his", "her", "their", "its", "my", "your", "our", "total",
            "altogether", "needed", "worth", "big", "bigger", "smaller", "longer", "shorter", "cheap", "cost",
            "red", "blue", "green", "yellow", "black", "white", "pink", "orange", "purple", "brown", "grey",
            "gray", "new", "old", "big", "little", "other", "another", "same", "so", "if", "then"}


def what_is_asked(sentence):
    """What does this question want? -> {"kind": ..., "thing": ..., "said": ...}.

    `kind` is one of needed / each / all / money / left / count, `thing` the noun the answer is about
    ("cars" for "how many cars are needed?"). It is a plain reading of the words: when they do not say
    which request it is, the kind stays "count" (the safe one), never a guess dressed as a fact.
    """
    q = (sentence or "").strip()
    kind = next((k for k, pat in _ASKS if re.search(pat, q, re.I)), "count")
    thing, phrase = "", ""
    m = _ASK_PHRASE.search(q) or _ASK_PHRASE.search(q.split(".")[-1])   # the question is usually the last sentence
    if m:                                          # "how many red pens are there" -> "red pens"
        phrase = m.group(1).strip()
        for word in reversed(phrase.split()):
            if word not in _NOTHING:
                thing = word
                break
    said = {"needed": f"how many {thing} are needed" if thing else "how many are needed",
            "each": f"how many {thing} each one gets" if thing else "how many each one gets",
            "all": f"how many {thing} in all" if thing else "how many in all",
            "money": "how much money", "left": f"how many {thing} are left" if thing else "how many are left",
            "count": f"the number of {thing}" if thing else "a number"}.get(kind, "a number")
    return {"kind": kind, "thing": thing, "phrase": phrase or thing, "said": said}


def asks_matches(recipe, asked):
    """Does this recipe answer the question that was asked? A recipe that answers "how many in each"
    must not fire on "how many are there"; a recipe that only says "count" must not fire on the
    questions whose request the reader is sure of. When the reader is not sure ("count"), any recipe
    may try - that is the honest default."""
    wants = recipe.get("asks")
    if not wants or asked.get("kind") in ("unknown", "count"):
        return True, ""
    wants = [wants] if isinstance(wants, str) else list(wants)
    if asked["kind"] in wants:
        return True, ""
    return False, f"the question asks '{asked['said']}', and this recipe answers {' or '.join(wants)}"


def not_about_matches(recipe, asked):
    """A program that counts the things inside the containers must not answer "how many containers",
    and one that adds two groups must not answer "how many red pens"."""
    not_about = recipe.get("not_about") or recipe.get("container")
    asked_about = asked.get("phrase") or asked.get("thing") or ""
    if not not_about or not asked_about:
        return True, ""
    if re.search(rf"\b(?:{not_about})\b", asked_about, re.I):
        return False, f"the question asks how many {asked_about}, which this program does not count"
    return True, ""