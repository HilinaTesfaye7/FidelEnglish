"""Record every sentence the course reads aloud, as small MP3 files for telegram/webapp/audio/.

Voice: Kokoro-82M (Apache-2.0 licence, free for commercial use), voice "af_heart" (American English).
Each file is named by an ID made from its text, the same way the course makes it (audioId in fidel-english.html).

Usage (from the FidelEnglish folder):
    python tools/make_audio.py <texts.json> <model.onnx> <af_heart.bin> <ffmpeg>
Already recorded files are skipped, so it can be stopped and started again.
"""
import json, os, subprocess, sys, time
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "telegram", "webapp", "audio")

def audio_id(t):
    h = 0x811c9dc5
    for ch in t:
        h ^= ord(ch); h = (h * 0x01000193) & 0xFFFFFFFF
    return "%08x" % h

def main():
    texts_path, model_path, voice_path, ffmpeg = sys.argv[1:5]
    from kokoro_onnx import Kokoro
    style = np.fromfile(voice_path, dtype=np.float32).reshape(-1, 1, 256)
    voices_npz = os.path.join(os.path.dirname(voice_path), "voices.npz")
    np.savez(voices_npz, af_heart=style)
    k = Kokoro(model_path, voices_npz)
    # The Hugging Face export wants the speed as a float; the library sends an int for that export.
    speed_type = next((i.type for i in k.sess.get_inputs() if i.name == "speed"), "")
    if "float" in speed_type:
        real_run = k.sess.run
        def run(names, inputs, *rest):
            if "speed" in inputs: inputs = dict(inputs, speed=np.asarray(inputs["speed"], dtype=np.float32))
            return real_run(names, inputs, *rest)
        k.sess.run = run
    texts = json.load(open(texts_path, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    done = skipped = 0; t0 = time.time()
    for n, text in enumerate(texts, 1):
        path = os.path.join(OUT, audio_id(text) + ".mp3")
        if os.path.exists(path) and os.path.getsize(path) > 500:
            skipped += 1; continue
        samples, sr = k.create(text, voice="af_heart", speed=1.0, lang="en-us")
        pad = np.zeros(int(sr * 0.12), dtype=np.float32)
        pcm = np.concatenate([pad, np.asarray(samples, dtype=np.float32).reshape(-1), pad])
        subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
                        "-c:a", "libmp3lame", "-b:a", "40k", path], input=pcm.tobytes(), check=True)
        done += 1
        if done % 50 == 0:
            rate = (time.time() - t0) / done
            print("%d/%d recorded, about %d min left" % (n, len(texts), rate * (len(texts) - n) / 60), flush=True)
    size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print("DONE: %d recorded, %d already there, %d files, %.1f MB" % (done, skipped, len(os.listdir(OUT)), size / 1e6), flush=True)

if __name__ == "__main__":
    main()
