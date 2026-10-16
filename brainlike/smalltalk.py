"""Small talk: greetings and phatic questions, answered, never learned from.

A "hi, how are you?" is not a lesson and not a claim about the world — it gets a
short friendly reply from fixed patterns and nothing is stored. Everything here
is deliberately anchored to the whole message, so "which" (which contains "hi")
or a story that mentions "hello" never matches. No imports: everything here is
language, nothing else.
"""
import re

_GREETING = re.compile(r"^(?:hi|hey|hello|good morning|good afternoon|good evening)[.!]*$", re.I)
_GREETING_QUESTION = re.compile(r"^(?:hi|hey|hello)[,!]?\s+how are you(?: doing| today)?[?!.]*$", re.I)
_HOW_ARE_YOU = re.compile(r"^how are you(?: doing| today)?[?!.]*$", re.I)
_THANKS = re.compile(r"^(?:thanks|thank you|thx)[.!]*$", re.I)
_BYE = re.compile(r"^(?:bye|goodbye|good ?night|see you(?: later)?)[.!]*$", re.I)
_WHO = re.compile(r"^(?:who are you|what are you|what is your name|your name)\??$", re.I)

_HELLO = ("Hello! Ask me some math, a story question, or a program to run — "
          "like 7*8, a story, or: plan: total = 6*7; total-2.")
_FINE = ("I'm doing well, thanks! What shall we work on — math, a story, or a program?")
_WELCOME = "You're welcome!"
_BYE_REPLY = "Goodbye! Come back any time."
_WHO_REPLY = ("I'm the Brain — a small AI that learns math, stories and programs "
              "from experience, with no big language model.")


def reply(text):
    """A friendly reply for a greeting, or None when this isn't small talk."""
    t = (text or "").strip()
    if _GREETING.match(t):
        return _HELLO
    if _GREETING_QUESTION.match(t) or _HOW_ARE_YOU.match(t):
        return _FINE
    if _THANKS.match(t):
        return _WELCOME
    if _BYE.match(t):
        return _BYE_REPLY
    if _WHO.match(t):
        return _WHO_REPLY
    return None
