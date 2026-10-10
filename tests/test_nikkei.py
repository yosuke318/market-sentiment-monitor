import unittest
from datetime import date

from nikkei import (
    build_average_message, build_jp_semiconductor_message, build_nt_ratio_message, build_sox_message,
    build_vi_message, nt_ratio, parse, position_message,
)

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
        msg = build_vi_message(parse(CSV))
        self.assertIn("日経平均VI: 22.58（2026-10-02 終値）", msg)
        self.assertIn("前日比: -0.34（22.92）", msg)
        # 1週間前の 9/25 はちょうど営業日
        self.assertIn("1週間前比: -1.42（24.00）", msg)
        # 30日前の 9/2 はデータがないので 9/1 と比べる
        self.assertIn("1ヶ月前比: +2.58（20.00）", msg)
        self.assertIn("1年前比: -2.42（25.00）", msg)


class BuildAverageMessageTest(unittest.TestCase):
    def test_percent_change_and_yen(self):
        rows = [(date(2026, 10, 1), 50000.0), (date(2026, 10, 2), 51000.0)]
        msg = build_average_message(rows)
        self.assertIn("日経平均株価: 51,000円（2026-10-02 終値）", msg)
        self.assertIn("前日比: +2.0%（50,000円）", msg)


class PositionTest(unittest.TestCase):
    def test_vi_message_has_position_line(self):
        # CSV の 5 営業日のうち 22.58 以上は 25.00・24.00・22.92・22.58 自身の 4 日 → 上位 80%
        msg = build_vi_message(parse(CSV))
        self.assertIn("水準: 2025-10以降の5営業日で上位80%（中央値 22.92、最高 25.00、最低 20.00）", msg)

    def test_highest_value_is_not_zero_percent(self):
        rows = [(date(2026, 10, d), float(d)) for d in range(1, 8)]
        self.assertIn("上位15%", position_message(rows))  # 1/7 = 14.3% → 切り上げ


class NtRatioTest(unittest.TestCase):
    AVERAGE = [(date(2026, 10, 1), 60000.0), (date(2026, 10, 2), 61000.0), (date(2026, 10, 5), 62000.0)]
    TOPIX = [(date(2026, 10, 1), 3000.0), (date(2026, 10, 5), 3100.0)]

    def test_only_common_dates(self):
        rows = nt_ratio(self.AVERAGE, self.TOPIX)
        self.assertEqual(rows, [(date(2026, 10, 1), 20.0), (date(2026, 10, 5), 20.0)])

    def test_message(self):
        rows = [(date(2026, 10, 1), 19.80), (date(2026, 10, 2), 20.00)]
        msg = build_nt_ratio_message(rows)
        self.assertIn("NT倍率（日経平均÷TOPIX）: 20.00（2026-10-02 終値）", msg)
        self.assertIn("前日比: +0.20（19.80）", msg)


class SemiconductorMessageTest(unittest.TestCase):
    ROWS = [(date(2026, 10, 1), 5000.0), (date(2026, 10, 2), 5150.0)]

    def test_sox_has_no_yen(self):
        msg = build_sox_message(self.ROWS)
        self.assertIn("SOX指数（米国の半導体株）: 5,150（2026-10-02 終値）", msg)
        self.assertIn("前日比: +3.0%（5,000）", msg)

    def test_jp_semiconductor_notes_etf(self):
        msg = build_jp_semiconductor_message(self.ROWS)
        self.assertIn("日経半導体株指数連動ETF 200A）: 5,150円", msg)
        self.assertIn("連動 ETF の価格で見ている", msg)
