"""調査用（一時）: 候補の URL ごとに応答と中身の先頭を出す。本番と同じ urllib とヘッダーで取る。"""

import re
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
NIKKEI = "https://indexes.nikkei.co.jp/nkave"
MOF = "https://www.mof.go.jp/jgbs/reference/interest_rate"
URLS = [
    # 対照: 本番で取れている CSV
    f"{NIKKEI}/historical/nikkei_stock_average_vi_daily_jp.csv",
    # PER の候補
    f"{NIKKEI}/archives/data?list=per",
    f"{NIKKEI}/archives/data?list=daily",
    f"{NIKKEI}/historical/nikkei_stock_average_per_daily_jp.csv",
    f"{NIKKEI}/historical/nikkei_stock_average_per_jp.csv",
    # 国債金利の候補
    f"{MOF}/jgbcm.csv",
    f"{MOF}/data/jgbcm_all.csv",
    f"{MOF}/jgbcm_all.csv",
]


def decode(body: bytes) -> str:
    for enc in ("utf-8", "cp932"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            pass
    return body.decode("utf-8", "replace")


for url in URLS:
    print("=" * 80)
    print(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read()
            print(f"status={res.status} type={res.headers.get('Content-Type')} bytes={len(body)}")
    except Exception as e:
        print(f"ERROR {e!r}")
        continue
    text = decode(body)
    if "<html" in text[:2000].lower():
        title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
        print("title:", title.group(1).strip() if title else None)
        print("challenge:", any(k in text for k in ("cf-chl", "challenge-platform", "Just a moment")))
        for href in sorted(set(re.findall(r'href="([^"]+\.csv[^"]*)"', text)))[:20]:
            print("csv link:", href)
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"[ \t\r]+", " ", plain)
        rows = [l.strip() for l in plain.splitlines() if re.search(r"20\d\d[./]\d\d[./]\d\d", l)]
        print("rows with dates:", len(rows))
        for l in rows[:8]:
            print("  ", l[:200])
        # 日付行が表の外にある場合に備えて、PER まわりの文字も少し出す
        for m in list(re.finditer(r"PER|株価収益率", plain))[:3]:
            print("  near:", re.sub(r"\s+", " ", plain[m.start(): m.start() + 300]))
    else:
        lines = text.splitlines()
        print("lines:", len(lines))
        for l in lines[:6] + ["..."] + lines[-4:]:
            print("  ", l[:200])
