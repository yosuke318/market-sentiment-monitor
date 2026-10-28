"""調査用（一時）: 日経平均の PER と財務省の国債金利（JGB）CSV が Actions から取れるかを確かめる。

本番と同じ urllib とヘッダーで取り、応答と中身の先頭・末尾を出す。
"""

import re
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
NIKKEI = "https://indexes.nikkei.co.jp"
MOF = "https://www.mof.go.jp/jgbs/reference/interest_rate"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as res:
        body = res.read()
        print(f"{url} -> status={res.status} type={res.headers.get('Content-Type')} bytes={len(body)}")
        return body


def table_rows(html: str) -> list[list[str]]:
    rows = re.findall(r"<tr.*?</tr>", html, re.S)
    return [[re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)] for r in rows]


print("=== 日経平均の PER（当月・過去の月）===")
for path in ("/nkave/archives/data?list=per", "/nkave/statistics/dataload?list=per&year=2025&month=10"):
    try:
        html = get(NIKKEI + path).decode("utf-8", "replace")
    except Exception as e:
        print(f"{path} ERROR {e!r}")
        continue
    rows = table_rows(html)
    print("rows:", len(rows), rows[:3], rows[-1:])
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    # PER が予想か前期実績かの注記があれば出す
    for key in ("予想", "前期", "実績"):
        for m in list(re.finditer(key, plain))[:2]:
            print(f"  [{key}]", plain[max(0, m.start() - 60): m.start() + 120])

print("=== 財務省の国債金利（JGB）CSV ===")
for url in (f"{MOF}/jgbcm.csv", f"{MOF}/data/jgbcm_all.csv"):
    try:
        lines = get(url).decode("cp932", "replace").splitlines()
    except Exception as e:
        print(f"{url} ERROR {e!r}")
        continue
    print("lines:", len(lines))
    for line in lines[:3] + ["..."] + lines[-3:]:
        print("  ", line[:160])
