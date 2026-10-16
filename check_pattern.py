import re
with open('brainlike/smalltalk.py', 'r') as f:
    content = f.read()
match = re.search(r'_GREETING_QUESTION = re\.compile\(r"([^"]+)"', content)
if match:
    print('Pattern:', match.group(1))
    # Test the pattern
    pattern = match.group(1)
    regex = re.compile(pattern, re.I)
    test = 'hi how are you doing?'
    print('Match:', regex.match('hi how are you doing?'))
    print('Match:', regex.match('hi how are you doing?'))