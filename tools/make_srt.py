#!/usr/bin/env python3
"""Gera legendas.srt (uma frase por bloco) a partir do projeto.json. Uso: python3 tools/make_srt.py projeto.json"""
import json, os, sys

def ts(t):
    ms = int(round(t * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"

for path in sys.argv[1:]:
    spec = json.load(open(path, encoding="utf-8"))
    out = os.path.join(os.path.dirname(path), "legendas.srt")
    with open(out, "w", encoding="utf-8") as f:
        for i, ln in enumerate(spec["lines"], 1):
            f.write(f"{i}\n{ts(ln['start'])} --> {ts(ln['start'] + ln['duration'])}\n{ln['text']}\n\n")
    print(out)
