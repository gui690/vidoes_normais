#!/usr/bin/env python3
"""Baixa cada clipe de 'segments[].url' e já corta só o trecho usado (economiza disco).

Uso: python3 tools/fetch_clips.py projeto.json
Cada segmento precisa de "url"; o arquivo vira clips_dir/segNN.mp4 e "clip" é preenchido.
"""
import json, os, subprocess, sys, urllib.request

spec_path = sys.argv[1]
spec = json.load(open(spec_path, encoding="utf-8"))
base = os.path.dirname(os.path.abspath(spec_path))
clips = spec["clips_dir"] if os.path.isabs(spec["clips_dir"]) else os.path.join(base, spec["clips_dir"])
os.makedirs(clips, exist_ok=True)
for i, s in enumerate(spec["segments"]):
    name = f"seg{i:02d}.mp4"
    out = os.path.join(clips, name)
    if not os.path.exists(out):
        raw = out + ".raw"
        subprocess.run(["curl", "-sSfL", "--max-time", "180", "-o", raw, s["url"]], check=True)
        dur = s["end"] - s["start"] + 2
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s.get("offset", 0)), "-i", raw,
                        "-t", f"{dur:.2f}", "-an", "-c", "copy", out], check=True)
        os.remove(raw)
    s["clip"], s["offset"] = name, 0
json.dump(spec, open(spec_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("ok", len(spec["segments"]), "clipes")
