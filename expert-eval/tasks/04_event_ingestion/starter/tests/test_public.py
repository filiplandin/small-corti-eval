import unittest

from events import EventFormatError, load_latest_events


class EventTests(unittest.TestCase):
    def test_keeps_latest_per_id_and_sorts(self):
        lines = [
            '{"id":"a","timestamp":"2026-01-01T10:00:00Z","kind":"created"}',
            '{"id":"b","timestamp":"2026-01-01T09:00:00+00:00","kind":"created"}',
            '{"id":"a","timestamp":"2026-01-01T11:00:00Z","kind":"updated"}',
        ]
        self.assertEqual([event["id"] for event in load_latest_events(lines)], ["b", "a"])
        self.assertEqual(load_latest_events(lines)[1]["kind"], "updated")

    def test_invalid_json_reports_line(self):
        with self.assertRaisesRegex(EventFormatError, "2"):
            load_latest_events(["", "not json"])


if __name__ == "__main__":
    unittest.main()
