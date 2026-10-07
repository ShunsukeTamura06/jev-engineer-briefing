"""measure.json から、LLM 所要時間が中央値の回を選び、demo_data.js を作る。"""
import json, pathlib, statistics

m = json.loads(pathlib.Path("measure.json").read_text(encoding="utf-8"))
ok = [r for r in m["runs"] if r["decision"]["status"] == 200 and r["llm"]["status"] == 200]
med = statistics.median_low(r["llm"]["elapsed"] for r in ok)
run = next(r for r in ok if r["llm"]["elapsed"] == med)
d = run["decision"]
data = {
    "model": m["model"], "statement": m["statement"], "question": m["question"], "options": m["options"],
    "decision": {"elapsed": d["elapsed"], "choice": d["choice"], "probs": d["probs"]},
    "llm": {"elapsed": run["llm"]["elapsed"], "chunks": run["llm"]["chunks"]},
    "runs": len(ok),
}
pathlib.Path("demo_data.js").write_text("window.DEMO = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
llm = [r["llm"]["elapsed"] for r in ok]
dm = [r["decision"]["elapsed"] for r in ok]
print(f"採用: LLM {run['llm']['elapsed']:.2f}s / Decision Model {d['elapsed']:.2f}s（{len(ok)}回中の中央値の回）")
print(f"範囲: LLM {min(llm):.2f}〜{max(llm):.2f}s / Decision Model {min(dm):.2f}〜{max(dm):.2f}s")
