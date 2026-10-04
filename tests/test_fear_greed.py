import unittest

from fear_greed import build_message, build_subject, change_message

DATA = {
    "score": 31.17,
    "rating": "fear",
    "timestamp": "2026-10-02T23:59:58+00:00",
    "previous_close": 28.09,
    "previous_1_week": 36.94,
    "previous_1_month": 46.06,
    "previous_1_year": 54.54,
}


class ChangeMessageTest(unittest.TestCase):
    def test_toward_greed(self):
        msg = change_message("extreme fear", "fear")
        self.assertIn("Extreme Fear（極度の恐怖） → Fear（恐怖）", msg)
        self.assertIn("楽観方向へ1段階", msg)

    def test_toward_fear_across_neutral(self):
        msg = change_message("greed", "fear")
        self.assertIn("悲観方向へ2段階", msg)
        self.assertIn("📉", msg)


class BuildMessageTest(unittest.TestCase):
    def test_no_change_has_no_alert(self):
        msg = build_message(DATA, "fear")
        self.assertNotIn("区分が変化しました", msg)
        self.assertIn("Fear & Greed Index: 31", msg)
        self.assertIn("前日比: +3.1（28）\n1週間前比: -5.8（37）", msg)
        self.assertIn("2026-10-03 08:59 JST", msg)

    def test_first_run_has_no_alert(self):
        self.assertNotIn("区分が変化しました", build_message(DATA, None))

    def test_change_alert_comes_first(self):
        msg = build_message(DATA, "extreme fear")
        self.assertTrue(msg.startswith("🔔 区分が変化しました"))


class BuildSubjectTest(unittest.TestCase):
    def test_no_change(self):
        self.assertEqual(build_subject(DATA, "fear"), "Fear & Greed 31: Fear")

    def test_change(self):
        self.assertEqual(
            build_subject(DATA, "extreme fear"),
            "【区分変化】Extreme Fear → Fear（Fear & Greed 31）",
        )


if __name__ == "__main__":
    unittest.main()
