"""OpenAI API 呼び出しの共通部品（キーは環境変数か同じフォルダの .env から読む。表示しない）。"""
import json, os, pathlib, urllib.request, urllib.error

def load_key():
    key = os.environ.get("OPENAI_API_KEY")
    env = pathlib.Path(__file__).with_name(".env")
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit("OPENAI_API_KEY が見つかりません（環境変数か demo-video/.env に設定）")
    return key

def post(path, body):
    req = urllib.request.Request(
        "https://api.openai.com" + path,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
