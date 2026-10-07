"""ライブ版（live.html）を Edge で実際に動かし、その画面を mp4 に録画する。

前提: Kev のサーバー（:8008）と serve_live.py（:8765）が起動していること。
やること: ページを開く → 準備完了を待つ → 「実行」を押す（本物の API 呼び出し）→ 結果が出てから数秒待つ → 録画を保存
出力: ../assets/demo_llm_vs_decision.mp4 と、画面に出た数字（rec_numbers.json）
"""
import json, pathlib, shutil, subprocess, time
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/"
HERE = pathlib.Path(__file__).parent
TMP = HERE / "_rec"
OUT = HERE.parent / "assets" / "demo_llm_vs_decision.mp4"
W, H = 1920, 1080

shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir()

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    ctx = browser.new_context(viewport={"width": W, "height": H},
                              record_video_dir=str(TMP), record_video_size={"width": W, "height": H})
    t_ctx = time.time()
    page = ctx.new_page()
    page.goto(URL)
    page.wait_for_function("(() => { const b = document.getElementById('run'); return b && !b.disabled; })()", timeout=90000)
    t_ready = time.time() - t_ctx
    page.wait_for_timeout(1500)                       # 実行前の待機画面を少し見せる
    box = page.locator("#run").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down(); page.wait_for_timeout(120); page.mouse.up()   # 本物のクリック（API を実際に呼ぶ）
    page.wait_for_selector(".foot.show", timeout=90000)
    page.wait_for_timeout(4500)                       # 結果を読む時間
    nums = page.evaluate("""() => ({
        llm: document.getElementById('t1').textContent,
        dm: document.getElementById('t2').textContent,
        foot: document.getElementById('foot').textContent,
        verdict: document.getElementById('vtxt').textContent,
        raw: document.getElementById('raw').textContent,
        log: document.getElementById('log').innerText })""")
    ctx.close(); browser.close()

webm = next(TMP.glob("*.webm"))
ss = max(0.0, t_ready - 0.8)                          # 読み込み中の空白を切り落とす
OUT.parent.mkdir(exist_ok=True)
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{ss:.2f}", "-i", str(webm),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
                "-movflags", "+faststart", "-an", str(OUT)], check=True)
(HERE / "rec_numbers.json").write_text(json.dumps(nums, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(nums, ensure_ascii=False, indent=1))
print("出力:", OUT, f"{OUT.stat().st_size/1e6:.1f} MB")
