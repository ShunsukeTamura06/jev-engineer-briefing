"""ライブ実行デモ用のローカルサーバー（http://127.0.0.1:8765/）。

ブラウザの live.html から、その場で本物の API を呼ぶための中継。
  - OpenAI の API キーはここ（サーバー側）だけが持つ。ブラウザには出さない。
  - 配るのは live.html だけ（.env などは配らない）。
前提: Decision Model（Kev）のサーバーがローカルで起動していること。README 参照。
"""
import json, pathlib, sys, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from measure import STATEMENT, QUESTION, CHOICES, MODEL, KEV_URL, kev_post, prep_kev, llm_body
from oai import load_key

HERE = pathlib.Path(__file__).parent
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s  %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/live.html"):
            data = (HERE / "live.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/api/config":
            self._json({"statement": STATEMENT, "question": QUESTION, "choices": CHOICES, "model": MODEL})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/prep":
            # Kev の先頭キャッシュから声明文を押し出す（キャッシュ命中で実力より速く見えないように）
            try:
                prep_kev()
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": repr(e)}, 502)
        elif self.path == "/api/kev":
            t = time.perf_counter()
            try:
                res = kev_post(STATEMENT)
                self._json({"server_elapsed": time.perf_counter() - t, "response": res})
            except Exception as e:
                self._json({"error": repr(e)}, 502)
        elif self.path == "/api/llm":
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(llm_body(), ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"})
            try:
                up = urllib.request.urlopen(req, timeout=120)
            except urllib.error.HTTPError as e:
                self._json({"error": e.read().decode("utf-8")[:300]}, e.code)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                for raw in up:                       # 受け取った行を、そのまま即座にブラウザへ流す
                    self.wfile.write(raw)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                up.close()
            self.close_connection = True
        else:
            self.send_error(404)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"ライブデモ: http://127.0.0.1:{PORT}/   （止めるときは Ctrl+C）")
    srv.serve_forever()
