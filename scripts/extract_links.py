import re

path = r"C:\Users\raphaeloliveira\.gemini\antigravity-ide\brain\d595c079-4ae3-4e9d-b37b-f71cb59b439c\.system_generated\steps\3745\content.md"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

matches = set(re.findall(r'/schultz0z0/Prometeus-Aion/(?:blob|tree)/main/([a-zA-Z0-9_\-\./]+)', text))
for m in sorted(matches):
    print(m)
