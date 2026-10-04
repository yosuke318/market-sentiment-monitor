import unittest
from datetime import date

from nikkei_vi import build_message, parse

CSV = """データ日付,終値,始値,高値,安値
"2025/10/01","25.00","25.00","25.00","25.00"
"2026/09/01","20.00","20.00","20.00","20.00"
"2026/09/25","24.00","24.00","24.00","24.00"
"2026/10/01","22.92","26.13","27.26","22.92"
"2026/10/02","22.58","27.48","27.74","22.58"
"本資料は日経の著作物であり、…"
"""


class ParseTest(unittest.TestCase):
    def test_skips_header_and_footer(self):
        rows = parse(CSV)
        self.assertEqual(rows[0], (date(2025, 10, 1), 25.0))
        self.assertEqual(rows[-1], (date(2026, 10, 2), 22.58))
        self.assertEqual(len(rows), 5)


class BuildMessageTest(unittest.TestCase):
    def test_comparisons_use_nearest_earlier_trading_day(self):
        msg = build_message(parse(CSV))
        self.assertIn("日経平均VI: 22.58（2026-10-02 終値）", msg)
        self.assertIn("前日比: -0.34（22.92）", msg)
        # 1週間前の 9/25 はちょうど営業日
        self.assertIn("1週間前比: -1.42（24.00）", msg)
        # 30日前の 9/2 はデータがないので 9/1 と比べる
        self.assertIn("1ヶ月前比: +2.58（20.00）", msg)
        self.assertIn("1年前比: -2.42（25.00）", msg)
