import unittest
from datetime import datetime, timedelta, timezone

import chart


def series(base: float, n: int = 60) -> list[tuple[datetime, float]]:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return [(today - timedelta(days=n - i), base + i) for i in range(n)]


class RenderDualAxisTest(unittest.TestCase):
    def test_renders_png_without_and_with_extra_axis(self):
        args = (("Nikkei 225", series(50000), "{:,.0f}"), ("Nikkei VI", series(20), "{:.2f}"))
        for extra in (None, ("TOPIX", series(3500), "{:,.0f}")):
            png = chart.render_dual_axis(*args, days=90, extra=extra)
            self.assertTrue(png.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
