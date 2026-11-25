"""The Inola answer -> record mapping and the batch file split, on made-up answers (no network)."""
import json
import unittest

import batch
from inola import record


class Record(unittest.TestCase):
    def test_answer_becomes_a_judged_record(self):
        body = {"version": "2.2.1", "output": {"answers": {"injection": {
            "noul": 0.97, "verdict": True, "threshold": 0.94, "verdicts": {"fpr_1e-03": True}}}}}
        r = record("d1", 200, body)
        self.assertEqual((r["judged"], r["score"], r["flagged"], r["version"]), (True, 0.97, True, "2.2.1"))
        self.assertEqual(r["verdicts"], {"fpr_1e-03": True})

    def test_refusal_is_not_judged_and_never_clean(self):
        r = record("d2", 413, "too_long", "2.2.1")
        self.assertFalse(r["judged"])
        self.assertIsNone(r["score"])
        self.assertIn("413", r["reason"])


class Split(unittest.TestCase):
    def test_files_respect_lines_and_characters(self):
        todo = [(f"d{i}", "x" * 10) for i in range(25)]
        files = list(batch.chunks(todo, "cordon-mini", "2.2.1", max_lines=10, max_chars=45))
        self.assertEqual([len(f) for f in files], [4, 4, 4, 4, 4, 4, 1])
        line = json.loads(files[0][0])
        self.assertEqual(line["body"], {"model": "cordon-mini", "input": {"state": "x" * 10}, "version": "2.2.1"})
        self.assertEqual(line["url"], "/v1/infer")


if __name__ == "__main__":
    unittest.main()
