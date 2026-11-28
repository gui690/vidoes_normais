#!/usr/bin/env python3
"""Monta um YouTube Short vertical (1080x1920) a partir de um arquivo de projeto JSON.

Uso:
    python3 tools/make_short.py projeto.json

O JSON tem:
{
  "narration": "caminho/narr.mp3",
  "clips_dir": "caminho/clips",
  "output": "caminho/saida.mp4",
  "lines": [{"text": "...", "start": 0.0, "duration": 4.0}, ...],
  "segments": [{"clip": "c00.mp4", "start": 0.0, "end": 4.05, "offset": 0.0}, ...],
  "music": "caminho/musica.mp3"   (opcional)
}
"""
import json
import os
import re
import subprocess
import sys
import tempfile

W, H, FPS = 1080, 1920, 30
WORDS_PER_CAPTION = 3
END_PAD = 1.0


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f"ffmpeg falhou ({r.returncode})")


def ass_time(t):
    t = max(t, 0)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_captions(lines, path):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter Display,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,620,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for ln in lines:
        words = ln["text"].split()
        chunks = [words[i:i + WORDS_PER_CAPTION] for i in range(0, len(words), WORDS_PER_CAPTION)]
        total = sum(len(" ".join(c)) for c in chunks) or 1
        t = ln["start"]
        for c in chunks:
            text = " ".join(c)
            dur = ln["duration"] * len(text) / total
            # números em amarelo
            styled = re.sub(r"(\d+[\d.,]*)", r"{\\c&H00FFFF&}\1{\\c&HFFFFFF&}", text.upper())
            # leve "pop" ao entrar
            pop = r"{\fscx80\fscy80\t(0,90,\fscx100\fscy100)}"
            events.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + dur)},Cap,,0,0,0,,{pop}{styled}")
            t += dur
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")


def main(spec_path):
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)
    base = os.path.dirname(os.path.abspath(spec_path))
    p = lambda x: x if os.path.isabs(x) else os.path.join(base, x)

    narration = p(spec["narration"])
    clips_dir = p(spec["clips_dir"])
    output = p(spec["output"])
    os.makedirs(os.path.dirname(output), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        segs = spec["segments"]
        seg_files = []
        for i, s in enumerate(segs):
            end = s["end"] + (END_PAD if i == len(segs) - 1 else 0)
            dur = end - s["start"]
            out = os.path.join(tmp, f"seg{i:02d}.mp4")
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"fps={FPS},setsar=1,format=yuv420p")
            run(["ffmpeg", "-y", "-ss", str(s.get("offset", 0)), "-i", os.path.join(clips_dir, s["clip"]),
                 "-t", f"{dur:.3f}", "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", out])
            seg_files.append(out)

        concat_list = os.path.join(tmp, "list.txt")
        with open(concat_list, "w") as f:
            f.writelines(f"file '{x}'\n" for x in seg_files)
        video = os.path.join(tmp, "video.mp4")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", video])

        subs = os.path.join(tmp, "caps.ass")
        build_captions(spec["lines"], subs)

        # duração exata do vídeo final: evita que o áudio (apad / música em loop) rode para sempre
        total = segs[-1]["end"] + END_PAD
        cmd = ["ffmpeg", "-y", "-i", video, "-i", narration]
        music = spec.get("music")
        if music:
            cmd += ["-stream_loop", "-1", "-i", p(music)]
            af = (f"[1:a]apad=whole_dur={total:.3f}[n];"
                  f"[2:a]atrim=0:{total:.3f},volume=0.12,afade=t=out:st={total - 1.5:.3f}:d=1.5[m];"
                  "[n][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
        else:
            af = f"[1:a]apad=whole_dur={total:.3f}[a]"
        cmd += ["-filter_complex", f"[0:v]ass={subs}[v];{af}", "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-c:a", "aac", "-b:a", "192k",
                "-t", f"{total:.3f}", output]
        try:
            run(cmd)
        except SystemExit:
            # o ffmpeg às vezes devolve ENOSPC (228) ao fechar o filtro com -shortest/apad;
            # se o arquivo ficou completo, está tudo certo
            chk = subprocess.run(["ffmpeg", "-v", "error", "-i", output, "-f", "null", "-"],
                                 capture_output=True, text=True)
            if chk.returncode != 0 or chk.stderr.strip():
                raise
    print(output)


if __name__ == "__main__":
    main(sys.argv[1])
