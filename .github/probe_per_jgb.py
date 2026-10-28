"""調査用（一時）2 回目: 日経の PER ページの表の HTML と、過去の月を選ぶフォームの形を出す。"""

import re
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
URL = "https://indexes.nikkei.co.jp/nkave/archives/data?list=per"

req = urllib.request.Request(URL, headers={"User-Agent": UA})
with urllib.request.urlopen(req, timeout=30) as res:
    html = res.read().decode("utf-8")

# 表の見出し（th）と、最初の 2 行・最後の 2 行の td
for i, table in enumerate(re.findall(r"<table.*?</table>", html, re.S)):
    print(f"--- table {i} ---")
    heads = [re.sub(r"<[^>]+>|\s+", " ", h).strip() for h in re.findall(r"<th.*?</th>", table, re.S)]
    print("th:", heads)
    rows = re.findall(r"<tr.*?</tr>", table, re.S)
    for r in rows[:3] + rows[-2:]:
        print("tr:", [re.sub(r"<[^>]+>|\s+", " ", c).strip() for c in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)])

# 年・月を切り替えるリンクやフォームの形
for m in sorted(set(re.findall(r'href="([^"]*list=per[^"]*)"', html)))[:15]:
    print("href:", m)
for m in re.findall(r"<form.*?</form>", html, re.S)[:3]:
    print("form:", re.sub(r"\s+", " ", m)[:600])
for m in re.findall(r"<select.*?</select>", html, re.S)[:3]:
    print("select:", re.sub(r"\s+", " ", m)[:400])
# JS でデータを取っている場合に備えて、data や ajax の URL らしきもの
for m in sorted(set(re.findall(r"[\"'](/nkave/[^\"']*(?:data|json|csv|ajax)[^\"']*)[\"']", html)))[:15]:
    print("url-like:", m)
