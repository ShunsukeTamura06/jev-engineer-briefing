"""OpenAI Decisions API に自分のキーでアクセスできるかを確かめる（キーは表示しない）。

形式はエラーメッセージから特定したもの（公式未公開、2026-10-07 時点）:
  POST /v1/decisions
  {"model","input","questions":[{"type":"choice","instructions","choices":[{"value"}...]}]}
  → {"answers":[{"type":"choice","choice","probabilities":[{"value","probability"}],"confidence"}]}
"""
import json, time
from oai import post

body = {
    "model": "gpt-6-luna",
    "input": "物価の見通しが上振れており、追加の利上げが適切と判断した。",
    "questions": [{
        "type": "choice",
        "instructions": "この金融政策の声明文のスタンスを選ぶ。",
        "choices": [{"value": "タカ"}, {"value": "中立"}, {"value": "ハト"}],
    }],
}
t = time.perf_counter()
status, text = post("/v1/decisions", body)
print(f"HTTP {status}  ({time.perf_counter()-t:.2f}s)")
print(json.dumps(json.loads(text), ensure_ascii=False, indent=2)[:2000])
