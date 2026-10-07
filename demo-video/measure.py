"""同じ声明文を、次の3つに同時に投げて実測し、measure.json に保存する。

  decision        … ローカルで動かした Kev-4B の /v1/systemone  ← 動画の右側に使う
  openai_decision … OpenAI Decisions API（参考。動画には出さない）
  llm             … OpenAI Chat API（gpt-6-luna、ストリーミング）          ← 動画の左側に使う

使い方: python measure.py [回数]   （Kev のサーバーを先に起動しておく。README 参照）
"""
import json, pathlib, sys, threading, time, urllib.request, urllib.error
from oai import load_key, post

MODEL = "gpt-6-luna"                      # LLM（Chat API）と OpenAI Decisions API のモデル
KEV_URL = "http://127.0.0.1:8008/v1/systemone"
STATEMENT = pathlib.Path(__file__).with_name("statement.txt").read_text(encoding="utf-8").strip()
QUESTION = "この日本銀行の公表文の金融政策のスタンス"
CHOICES = [
    {"value": "タカ派", "description": "今後の利上げ、金融緩和の縮小、または物価上振れリスクを明確に示している"},
    {"value": "中立", "description": "政策変更の方向性が明確でない、または引き締め・緩和の材料が均衡している"},
    {"value": "ハト派", "description": "今後の利下げ、追加緩和、または景気・物価の下振れリスクを明確に示している"},
    {"value": "判断困難", "description": "根拠が不足している、または複数の方向性が混在して分類できない"},
]
OPTIONS = [c["value"] for c in CHOICES]


def kev_request(state):
    return {"model": "kev-latest", "state": state, "questions": {"stance": {
        "type": "choice", "instructions": QUESTION,
        "criteria": {c["value"]: c["description"] for c in CHOICES}}}}


def kev_post(state):
    req = urllib.request.Request(KEV_URL, data=json.dumps(kev_request(state), ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def prep_kev():
    """初期化（最初の1回は遅い）と、サーバーの先頭キャッシュ（4件）から声明文を押し出す。
    声明文そのものは変えない。別の短い文章を5回送って、LRU から追い出す。"""
    for i in range(5):
        kev_post(f"準備用の文章 {i}。金融政策とは関係のないダミーです。")


def run_decision(out, t0):
    try:
        res = kev_post(STATEMENT)
        a = res["answers"]["stance"]
        out["decision"] = {"status": 200, "elapsed": time.perf_counter() - t0, "choice": a["choice"],
                           "probs": a["probabilities"], "confidence": a.get("confidence")}
    except Exception as e:                                   # サーバー未起動など
        out["decision"] = {"status": 0, "error": repr(e)}


def run_openai_decision(out, t0):
    body = {"model": MODEL, "input": STATEMENT, "questions": [
        {"type": "choice", "instructions": QUESTION, "choices": CHOICES}]}
    status, text = post("/v1/decisions", body)
    d = {"status": status, "elapsed": time.perf_counter() - t0}
    if status == 200:
        a = json.loads(text)["answers"][0]
        d.update(choice=a["choice"], probs={p["value"]: p["probability"] for p in a["probabilities"]},
                 confidence=a.get("confidence"))
    else:
        d["error"] = text[:300]
    out["openai_decision"] = d


def llm_body():
    opts = "／".join(OPTIONS)
    lines = "\n".join(f"- {c['value']}：{c['description']}" for c in CHOICES)
    prompt = (f"次の文書を読み、{QUESTION}を、{opts}のどれか答えてください。\n{lines}\n"
              f"まず理由を述べ、最後に『結論：{opts}』の形で答えてください。\n\n" + STATEMENT)
    return {"model": MODEL, "stream": True, "messages": [{"role": "user", "content": prompt}]}


def run_llm(out, t0):
    body = llm_body()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {load_key()}", "Content-Type": "application/json"})
    chunks = []
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    continue
                for c in json.loads(line[5:]).get("choices", []):
                    s = (c.get("delta") or {}).get("content")
                    if s:
                        chunks.append({"t": time.perf_counter() - t0, "text": s})
        out["llm"] = {"status": 200, "elapsed": time.perf_counter() - t0, "chunks": chunks}
    except urllib.error.HTTPError as e:
        out["llm"] = {"status": e.code, "error": e.read().decode("utf-8")}


def one_run():
    prep_kev()                                               # 計測の外
    out, t0 = {}, time.perf_counter()
    ts = [threading.Thread(target=f, args=(out, t0)) for f in (run_decision, run_openai_decision, run_llm)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    runs = [one_run() for _ in range(n)]
    pathlib.Path("measure.json").write_text(json.dumps(
        {"model": MODEL, "statement": STATEMENT, "question": QUESTION, "options": OPTIONS, "runs": runs},
        ensure_ascii=False, indent=1), encoding="utf-8")
    def fmt(p): return {k: round(v, 3) for k, v in p.items()}
    for i, r in enumerate(runs):
        d, o, l = r["decision"], r["openai_decision"], r["llm"]
        print(f"[{i}] Kev(ローカル): " + (f"{d['elapsed']:.2f}s  {d['choice']}  {fmt(d['probs'])}" if d["status"] == 200 else d))
        print(f"    OpenAI Dec.  : " + (f"{o['elapsed']:.2f}s  {o['choice']}  {fmt(o['probs'])}" if o["status"] == 200 else o))
        if l["status"] == 200:
            txt = "".join(c["text"] for c in l["chunks"])
            print(f"    LLM          : {l['elapsed']:.2f}s  {len(txt)}字  …{txt[-14:].strip()}")
        else:
            print("    LLM:", l)
