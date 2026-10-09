"""How the brain recognises an English question or lesson (perception), and
hands it to the English region (which does the learning).

  plural of mouse              -> word form          plural of mouse = mice   (teach)
  opposite of hot              -> relation           opposite of hot = cold
  is a dog an animal?          -> is-a check         a dog is an animal       (teach)
  big means large              -> synonym (teach)
  word class of happy          -> noun / verb / adjective / adverb
  She (go) to school every day -> gap-fill           ... = goes               (teach)
"""
import re

_FORMS = {"plural": "plural", "past": "past", "past tense": "past", "ing": "ing", "-ing": "ing",
          "ing form": "ing", "-ing form": "ing", "third": "third", "third person": "third", "he/she form": "third",
          "comparative": "comparative", "superlative": "superlative", "article": "article",
          "adverb": "adverb", "negative": "negative", "prefix opposite": "negative"}
_FORM_Q = re.compile(r"^(?:what(?:'s| is) )?(?:the )?(plural|past tense|past|-?ing form|-?ing|third person|third|he/she form|"
                     r"comparative|superlative|article|adverb|negative|prefix opposite)(?: form)? (?:of|for) (?:the word )?([a-z]+)\s*\??$", re.I)
_REL_Q = re.compile(r"^(?:what(?:'s| is) )?(?:the |an? )?(opposite|antonym|synonym)s? (?:of|for) ([a-z]+)\s*\??$", re.I)
_REL_CHECK = re.compile(r"^(?:is|are) (?:the word )?([a-z]+) (?:an? )?(synonym|antonym|opposite) (?:of|for) ([a-z]+)\s*\??$", re.I)
_ISA_Q = re.compile(r"^(?:is|are) (?:an? )?([a-z]+) (?:an? )([a-z]+)\s*\??$", re.I)
_ISA_TEACH = re.compile(r"^(?:an? )?([a-z]+) (?:is|are) (?:an? )([a-z]+)\s*\.?$", re.I)
_MEANS = re.compile(r"^([a-z]+) means ([a-z]+)\s*\.?$", re.I)
_CLASS_Q = re.compile(r"^(?:what(?:'s| is) )?(?:the )?(?:word class|part of speech|kind of word) (?:of|is) ([a-z]+)\s*\??$", re.I)
_GAP = re.compile(r"\([a-zA-Z]+\)")
_REL_NAME = {"opposite": "antonym", "antonym": "antonym", "synonym": "synonym"}


def read(text):
    """-> (kind, parts) for an English question, or None. kind: form, find, check, isa, class, gap."""
    t = text.strip()
    if _GAP.search(t) and not re.search(r"[\d+*/=]", _GAP.sub("", t)):
        return "gap", {"sentence": t}
    if m := _FORM_Q.match(t):
        return "form", {"form": _FORMS[m[1].lower()], "word": m[2].lower()}
    if m := _REL_Q.match(t):
        return "find", {"relation": _REL_NAME[m[1].lower()], "word": m[2].lower()}
    if m := _REL_CHECK.match(t):
        return "check", {"relation": _REL_NAME[m[2].lower()], "a": m[1].lower(), "b": m[3].lower()}
    if m := _CLASS_Q.match(t):
        return "class", {"word": m[1].lower()}
    if m := _ISA_Q.match(t):
        return "isa", {"a": m[1].lower(), "b": m[2].lower()}
    return None


def read_lesson(text):
    """A lesson with no '=': 'a dog is an animal', 'big means large'. -> (kind, parts) or None."""
    t = text.strip()
    if m := _MEANS.match(t):
        return "teach_relation", {"relation": "synonym", "a": m[1].lower(), "b": m[2].lower()}
    if m := _ISA_TEACH.match(t):
        return "teach_relation", {"relation": "is-a", "a": m[1].lower(), "b": m[2].lower()}
    return None


def ask(english, kind, p):
    """Answer an English question. -> reply dict."""
    if kind == "form":
        word, how = english.form(p["form"], p["word"])
        return {"answer": word, "how": how, "question": f"{p['form']} of {p['word']}"}
    if kind == "find":
        word, how = english.find(p["relation"], p["word"])
        return {"answer": word, "how": how, "question": f"{'opposite' if p['relation'] == 'antonym' else 'synonym'} of {p['word']}"}
    if kind == "check":
        yes, how = english.related(p["relation"], p["a"], p["b"])
        return {"answer": None if yes is None else ("yes" if yes else "no"), "how": how,
                "question": f"is {p['a']} {'an opposite' if p['relation'] == 'antonym' else 'a synonym'} of {p['b']}"}
    if kind == "isa":
        yes, how = english.related("is-a", p["a"], p["b"])
        return {"answer": None if yes is None else ("yes" if yes else "no"), "how": how,
                "question": f"is a {p['a']} a {p['b']}"}
    if kind == "class":
        cls, how = english.word_class(p["word"])
        return {"answer": cls, "how": how, "question": f"word class of {p['word']}"}
    if kind == "gap":
        word, how = english.fill(p["sentence"])
        return {"answer": word, "how": how, "question": p["sentence"]}
    raise ValueError(f"unknown English question {kind}")


def teach(english, kind, p, answer):
    """Teach the answer to an English question. -> reply dict (what it would have said, and what it noticed)."""
    answer = str(answer).strip()
    if kind in ("form", "find", "class", "gap") and not re.fullmatch(r"[A-Za-z' -]+", answer):
        raise ValueError(f"'{answer}' isn't a word, so I won't learn it as the answer to '{kind}'")
    if kind == "form":
        own, how, right = english.teach_form(p["form"], p["word"], answer)
    elif kind == "find":
        own, how = english.find(p["relation"], p["word"])
        english.teach_relation(p["relation"], p["word"], answer)
        right = own == answer.lower()
    elif kind == "class":
        own, how = english.word_class(p["word"])
        english.teach_class(p["word"], answer.lower())
        right = own == answer.lower()
    elif kind == "gap":
        own = english.teach_sentence(p["sentence"], answer)
        how, right = "", own == answer.lower()
    elif kind in ("check", "isa"):
        relation = "is-a" if kind == "isa" else p["relation"]
        yes = answer.lower() in ("yes", "true", "y")
        own, how = english.related(relation, p["a"], p["b"])
        if yes:
            english.teach_relation(relation, p["a"], p["b"])
        right = own == yes
    else:
        raise ValueError(f"can't teach {kind}")
    return {"learned": answer, "own_answer": own, "agreed": right, "how": how,
            "proposed_english_rule": english.notice(p.get("form")) if kind == "form" else None}
