import unittest
from datetime import datetime, timedelta, timezone

import yahoo

JST = timezone(timedelta(hours=9))


class ParseTest(unittest.TestCase):
    def test_skips_missing_close_and_uses_exchange_date(self):
        closes = [
            (datetime(2026, 10, 1, tzinfo=JST), 3500.5),
            (datetime(2026, 10, 2, tzinfo=JST), float("nan")),
            (datetime(2026, 10, 5, tzinfo=JST), None),
            (datetime(2026, 10, 6, tzinfo=JST), 3512.25),
        ]
        rows = yahoo.parse(closes)
        self.assertEqual([(d.isoformat(), v) for d, v in rows], [("2026-10-01", 3500.5), ("2026-10-06", 3512.25)])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            yahoo.parse([(datetime(2026, 10, 1, tzinfo=JST), float("nan"))])


if __name__ == "__main__":
    unittest.main()
