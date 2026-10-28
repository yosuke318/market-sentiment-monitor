import unittest
from datetime import date

import valuation

# 日経のヒストリカルデータ（list=per）の表の形
PER_HTML = """
<table class="table">
<tr><th>日付</th><th>加重平均(倍)</th><th>指数ベース(倍)</th></tr>
<tr><td>2026.10.26</td><td>16.65</td><td>20.53</td></tr>
<tr><td>2026.10.27</td><td> 16.75 </td><td>20.89</td></tr>
<tr><td>2026.10.28</td><td>-</td><td>-</td></tr>
</table>
"""

# 財務省の国債金利情報 CSV の形（当月分）
JGB_CSV = """国債金利情報 (令和8年10月),,,,,,,,,,,,,,,(単位 : %)
基準日,1年,2年,3年,4年,5年,6年,7年,8年,9年,10年,15年,20年,25年,30年,40年
R8.10.26,1.649,1.888,1.988,2.131,2.241,2.323,2.425,2.574,2.699,2.824,3.361,3.63,3.928,3.884,3.9
R8.10.27,1.651,1.888,1.991,2.137,2.246,2.329,2.435,2.579,2.703,2.829,3.362,3.638,3.932,3.895,3.912
,,,,,,,,,,,,,,,
※最新のcsvデータがダウンロードできない場合、ご利用のブラウザにおいてキャッシュの削除を実施し再度ダウンロードください。,,,,,,,,,,,,,,,
"""


class ParsePerTest(unittest.TestCase):
    def test_reads_rows_and_skips_header_and_missing(self):
        self.assertEqual(
            valuation.parse_per_html(PER_HTML),
            [(date(2026, 10, 26), 16.65, 20.53), (date(2026, 10, 27), 16.75, 20.89)],
        )

    def test_months_needed_for_comparisons(self):
        # 前月・前々月と、1年前の月とその前月
        self.assertEqual(
            valuation.per_months(date(2026, 1, 5)), [(2025, 12), (2025, 11), (2025, 1), (2024, 12)]
        )


class ParseJgbTest(unittest.TestCase):
    def test_reads_10y_column(self):
        self.assertEqual(
            valuation.parse_jgb_csv(JGB_CSV),
            [(date(2026, 10, 26), 2.824), (date(2026, 10, 27), 2.829)],
        )

    def test_era_dates_and_missing_values(self):
        self.assertEqual(valuation.parse_era_date("S49.9.24"), date(1974, 9, 24))
        self.assertEqual(valuation.parse_era_date("H31.4.26"), date(2019, 4, 26))
        self.assertEqual(valuation.parse_era_date("R1.5.7"), date(2019, 5, 7))
        csv = "基準日,1年,10年\nS49.9.24,10.327,-\n"
        self.assertEqual(valuation.parse_jgb_csv(csv), [])


class YieldSpreadTest(unittest.TestCase):
    def test_uses_latest_yield_on_or_before_per_date(self):
        per = [(date(2026, 10, 27), 20.0)]
        # 10/27 の利回りがまだ公表されていない場合は 10/26 を使う
        jgb = [(date(2026, 10, 26), 3.0)]
        self.assertEqual(valuation.yield_spread(per, jgb), [(date(2026, 10, 27), 2.0)])

    def test_message(self):
        per = valuation.parse_per_html(PER_HTML)
        jgb = valuation.parse_jgb_csv(JGB_CSV)
        msg = valuation.build_message(per, jgb)
        self.assertIn("日経平均PER: 16.75倍（加重平均）/ 20.89倍（指数ベース）（2026-10-27）", msg)
        self.assertIn("前日比: +0.10（16.65）", msg)
        self.assertIn("日本10年債利回り: 2.829%（2026-10-27）", msg)
        self.assertIn("前日比: +0.005pt（2.824%）", msg)
        # 100 / 16.75 - 2.829 = 3.141…
        self.assertIn("イールドスプレッド（株式益回り−10年債利回り）: +3.14pt（PER 10/27・利回り 10/27）", msg)
        # 100 / 20.89 - 2.829 = 1.958…
        self.assertIn("指数ベースPERでは +1.96pt", msg)

    def test_message_when_one_side_failed(self):
        msg = valuation.build_message(None, valuation.parse_jgb_csv(JGB_CSV))
        self.assertIn("日経平均のPERは取得に失敗しました", msg)
        self.assertIn("日本10年債利回り: 2.829%", msg)
        self.assertNotIn("イールドスプレッド", msg)


if __name__ == "__main__":
    unittest.main()
