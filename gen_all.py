# 补全配音 Fill in missing audio
# 给 missing_audio.json 里的句子和词生成女声（晓晓）和男声（云扬），
# 先放进 audio 文件夹，最后打包成一个文件 audio-x-xxxx.bin，对照表写进同一个文件夹里的 content.json。
# 用法（在 Mac「终端」里）：
#   cd ~/网络语音/网站上传/这次上传GitHub-v155 && python3 gen_all.py
# 大约 10–15 分钟。完成后只需要上传：content.json、audio-x-xxxx.bin、index.html、sw.js（audio 文件夹不用上传）。
import asyncio, json, os, hashlib, sys
try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts 没装。先运行： python3 -m pip install --user edge-tts")
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "content.json")
c = json.load(open(P, encoding="utf-8"))
want = json.load(open(os.path.join(HERE, "missing_audio.json"), encoding="utf-8"))
aud = c.setdefault("audio", {})
VOICES = {"f": "zh-CN-XiaoxiaoNeural", "m": "zh-CN-YunyangNeural"}
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
failed = []

async def one(v, text, sem):
    rel = "audio/%s_%s.mp3" % (v, hashlib.md5(text.encode("utf-8")).hexdigest()[:10])
    path = os.path.join(HERE, rel)
    if not (os.path.exists(path) and os.path.getsize(path) > 500):
        async with sem:
            for attempt in range(4):
                try:
                    await edge_tts.Communicate(text, VOICES[v], rate=("-15%" if len(text) <= 4 else "-5%")).save(path)
                    if os.path.getsize(path) > 500:
                        break
                except Exception:
                    await asyncio.sleep(2 + attempt * 3)
            else:
                failed.append(text)
                return

async def main():
    sem = asyncio.Semaphore(4)
    jobs = [one(v, t, sem) for v in VOICES for t in want]
    done = 0
    for f in asyncio.as_completed(jobs):
        await f
        done += 1
        if done % 50 == 0:
            print("  %d / %d" % (done, len(jobs)), flush=True)

asyncio.run(main())
# 打包成一个文件 Pack everything into one file
data = bytearray(); pack = {}
for v in VOICES:
    pack[v] = {}
    for t in want:
        path = os.path.join(HERE, "audio/%s_%s.mp3" % (v, hashlib.md5(t.encode("utf-8")).hexdigest()[:10]))
        if os.path.exists(path) and os.path.getsize(path) > 500:
            b = open(path, "rb").read()
            pack[v][t] = [len(data), len(b)]
            data += b
name = "audio-x-%s.bin" % hashlib.md5(bytes(data)).hexdigest()[:8]
open(os.path.join(HERE, name), "wb").write(data)
pack["file"] = name
c["audioPack"] = pack
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("打包好了 Packed:", name, "%.1f MB" % (len(data) / 1e6))
print("完成 Done.", len(want), "条，失败", len(set(failed)), "条")
if failed:
    print("没成功的（再运行一次就会补上）:", "、".join(sorted(set(failed))[:20]))
