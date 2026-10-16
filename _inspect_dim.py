live = open("brainlike/storyreader.py", encoding="utf-8", newline="").read()
end = '_CUBE_WORDS = {"cubic"}'
j = live.index(end) + len(end)
print("AFTER:", repr(live[j:j + 140]))
start = "# Dimension adjectives"
i = live.index(start)
print("BEFORE:", repr(live[i - 140:i]))
print("has _DIM_DESC:", "_DIM_DESC" in live, "| has _CUBE:", end in live)
