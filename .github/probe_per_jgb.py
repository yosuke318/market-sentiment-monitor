"""調査用（一時）3 回目: PER が予想か前期実績かの注記と、過去の月の取り方を確かめる。"""

import re
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
BASE = "https://indexes.nikkei.co.jp"


def get(path: str) -> str:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        print(f"{path} -> status={res.status} type={res.headers.get('Content-Type')}")
        return res.read().decode("utf-8", "replace")


html = get("/nkave/archives/data?list=per")
plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
for key in ("予想", "前期", "実績", "※", "注"):
    for m in list(re.finditer(key, plain))[:3]:
        print(f"[{key}]", plain[max(0, m.start() - 80): m.start() + 160])

for path in (
    "/nkave/statistics/dataload?list=per&year=2025&month=10",
    "/nkave/archives/data?list=per&year=2025&month=10",
):
    try:
        body = get(path)
    except Exception as e:
        print(path, "ERROR", repr(e))
        continue
    rows = re.findall(r"<tr.*?</tr>", body, re.S)
    cells = [[re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)] for r in rows]
    print("rows:", len(cells), cells[:3], cells[-1:] if cells else None)
