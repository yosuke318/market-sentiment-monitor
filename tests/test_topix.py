import unittest

import topix

PAYLOAD = {
    "chart": {
        "result": [{
            "meta": {"gmtoffset": 32400},
            # 2026-10-01 00:00 UTC / 2026-10-02 00:00 UTC / 2026-10-05 00:00 UTC
            "timestamp": [1790812800, 1790899200, 1791158400],
            "indicators": {"quote": [{"close": [3500.5, None, 3512.25]}]},
        }]
    }
}


class ParseTest(unittest.TestCase):
    def test_skips_null_close_and_uses_exchange_date(self):
        rows = topix.parse(PAYLOAD)
        self.assertEqual([v for _, v in rows], [3500.5, 3512.25])
        # 現地時間（+9h）の日付になる
        self.assertEqual([d.isoformat() for d, _ in rows], ["2026-10-01", "2026-10-05"])

    def test_empty_raises(self):
        payload = {"chart": {"result": [{
            "meta": {}, "timestamp": [1790812800], "indicators": {"quote": [{"close": [None]}]},
        }]}}
        with self.assertRaises(ValueError):
            topix.parse(payload)


if __name__ == "__main__":
    unittest.main()
