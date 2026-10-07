"""ローカルで動かした Kev-4B の /v1/systemone に、同じ声明文・同じ4択を投げて確率と時間を見る。"""
import json, sys, time, urllib.request
from measure import QUESTION, CHOICES, STATEMENT

URL = "http://127.0.0.1:8008/v1/systemone"
body = {
    "model": "kev-latest",
    "state": STATEMENT,
    "questions": {"stance": {
        "type": "choice",
        "instructions": QUESTION,
        "criteria": {c["value"]: c["description"] for c in CHOICES},
    }},
}

def call(b):
    req = urllib.request.Request(URL, data=json.dumps(b, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.load(r)
    return time.perf_counter() - t, res

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    for i in range(n):
        dt, res = call(body)
        a = res["answers"]["stance"]
        probs = {k: round(v, 3) for k, v in a["probabilities"].items()}
        print(f"[{i}] {dt:.2f}s  {a['choice']}  {probs}  conf={a.get('confidence')}")
