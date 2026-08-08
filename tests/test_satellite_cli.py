import unittest

from zenit_geospatial.satellite_cli import build_parser


class SatelliteCliTests(unittest.TestCase):
    def test_parser_requires_explicit_segment_zone_and_dates(self) -> None:
        arguments = build_parser().parse_args(
            [
                "--segment-index", "195", "--zone", "left",
                "--from-date", "2026-07-01", "--to-date", "2026-08-07",
            ]
        )

        self.assertEqual(arguments.segment_index, 195)
        self.assertEqual(arguments.zone, "left")
        self.assertEqual(arguments.limit, 5)


if __name__ == "__main__":
    unittest.main()
