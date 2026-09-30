from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "auxiliary/scripts" / "evaluation"))
sys.path.insert(0, str(ROOT / "auxiliary/scripts"))

from import_verbnet import render_requirement, restriction_expression


class EvaluationTests(unittest.TestCase):
    def test_verbnet_nested_role_requirements_are_preserved(self) -> None:
        node = ET.fromstring(
            """
            <SELRESTRS logic="or">
              <SELRESTR Value="+" type="animate" />
              <SELRESTR Value="+" type="organization" />
            </SELRESTRS>
            """
        )
        self.assertEqual(
            render_requirement(restriction_expression(node), "Agent"),
            "AnyOf [HasSort Animate,HasSort Organization]",
        )

    def test_verbnet_negative_role_requirement_is_preserved(self) -> None:
        node = ET.fromstring(
            """
            <SELRESTRS>
              <SELRESTR Value="-" type="location" />
            </SELRESTRS>
            """
        )
        self.assertEqual(
            render_requirement(restriction_expression(node), "Theme"),
            "Not (HasSort Place)",
        )

    def test_committed_action_roles_include_announce_subject(self) -> None:
        with (ROOT / "auxiliary/data" / "verbnet-action-roles.tsv").open(
            encoding="utf-8", newline=""
        ) as source:
            rows = csv.DictReader(source, delimiter="\t")
            matching = [
                row
                for row in rows
                if row["lemma"] == "announce"
                and row["hole_role"] == "SubjectHole"
                and row["mapping_status"] == "compiled"
            ]
        self.assertTrue(matching)
        self.assertIn(
            "AnyOf [HasSort Animate,HasSort Organization]",
            {row["requirement"] for row in matching},
        )


if __name__ == "__main__":
    unittest.main()
