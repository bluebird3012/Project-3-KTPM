"""Strict Level 2 offline verification: schema, immutability, anti-hardcoding, and mock locator swap."""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
import unittest
from unittest.mock import patch

from core import testing_items as TI
from core.config import ROOT_DIR
from pages import add_quiz_page


class TestTestingItemsLevel2(unittest.TestCase):
    def test_loaded_items_are_immutable_mapping_proxy(self):
        self.assertIsInstance(TI.ITEMS, MappingProxyType)
        with self.assertRaises(TypeError):
            TI.ITEMS["NEW_KEY"] = ("id", "x")  # type: ignore[index]

    def test_schema_validation_rejects_bad_configs(self):
        dummy_path = Path("config/testing_items.csv")

        # 1. Invalid header
        with self.assertRaisesRegex(ValueError, "Invalid testing-items header"):
            TI.load_items(dummy_path, raw=b"name,type,value\nA,id,x\n")

        # 2. Duplicate key
        with self.assertRaisesRegex(ValueError, "Duplicate testing item"):
            TI.load_items(dummy_path, raw=b"item_name,item_type,item_value\nA,id,x\nA,id,y\n")

        # 3. Empty value
        with self.assertRaisesRegex(ValueError, "Empty item_value"):
            TI.load_items(dummy_path, raw=b"item_name,item_type,item_value\nA,id,   \n")

        # 4. Unsupported item_type
        with self.assertRaisesRegex(ValueError, "Unsupported item_type"):
            TI.load_items(dummy_path, raw=b"item_name,item_type,item_value\nA,regex,abc\n")

        # 5. Invalid path (not relative to site root)
        with self.assertRaisesRegex(ValueError, "Expected site-relative path"):
            TI.load_items(dummy_path, raw=b"item_name,item_type,item_value\nP,path,http://evil/x\n")

        # 6. Invalid URL
        with self.assertRaisesRegex(ValueError, "Expected absolute HTTP\\(S\\) URL"):
            TI.load_items(dummy_path, raw=b"item_name,item_type,item_value\nU,url,/relative/path\n")

        # 7. Missing key raises ValueError (zero fallback)
        with self.assertRaisesRegex(ValueError, "Missing testing item"):
            TI.item("NON_EXISTENT_ITEM")

    def test_no_hardcoded_moodle_urls_paths_or_locators_in_python(self):
        forbidden_literals = [
            "http://127.0.0.1:9502",
            "/course/modedit.php",
            "/login/index.php",
            "/mod/quiz/view.php",
            "id_submitbutton2",
            "id_submitbutton",
            "id_boundary_add_fields",
            "id_name",
            "id_showdescription",
            "id_error_name",
            "id_error_gradepass",
            "id_introeditor",
            "page-mod-quiz-view",
            "feedbackboundaries[0]",
        ]
        # Note: 'feedbackboundaries[0]' IS a CSV logical field name in FIELD_ITEM_KEYS & apply_input_dict,
        # so check strict CSS/ID/URL/path literals in pages/, test_groups/, core/config.py
        strict_forbidden = [s for s in forbidden_literals if s != "feedbackboundaries[0]"]
        checked_files = (
            list((ROOT_DIR / "pages").glob("*.py"))
            + list((ROOT_DIR / "test_groups").glob("*.py"))
            + [ROOT_DIR / "core" / "config.py"]
        )
        self.assertGreaterEqual(len(checked_files), 8)
        for py_file in checked_files:
            content = py_file.read_text(encoding="utf-8")
            for literal in strict_forbidden:
                self.assertNotIn(
                    literal,
                    content,
                    f"Hardcoded Moodle testing item {literal!r} found in {py_file.relative_to(ROOT_DIR)}",
                )

    def test_changing_submit_locator_in_csv_changes_selenium_arguments(self):
        raw_original = TI.TESTING_ITEMS_FILE.read_text(encoding="utf-8-sig")
        self.assertIn("SUBMIT_RETURN_BUTTON,id,id_submitbutton2", raw_original)

        swapped_csv = raw_original.replace(
            "SUBMIT_RETURN_BUTTON,id,id_submitbutton2",
            "SUBMIT_RETURN_BUTTON,css,input[name='submitbutton2']",
        )
        swapped_items = TI.load_items(TI.TESTING_ITEMS_FILE, raw=swapped_csv.encode("utf-8"))

        calls_before = []
        calls_after = []

        def record_before(browser, by, locator, timeout, label):
            calls_before.append((by, locator, label))

        def record_after(browser, by, locator, timeout, label):
            calls_after.append((by, locator, label))

        page = add_quiz_page.AddQuizPage(browser=object(), base_url="http://127.0.0.1:9502", timeout=10)
        with patch.object(add_quiz_page, "click_visible", side_effect=record_before):
            page.submit("save_return")

        with patch.object(TI, "ITEMS", swapped_items):
            with patch.object(add_quiz_page, "click_visible", side_effect=record_after):
                page.submit("save_return")

        self.assertEqual(calls_before, [("id", "id_submitbutton2", "Save and return to course")])
        self.assertEqual(
            calls_after,
            [("css selector", "input[name='submitbutton2']", "Save and return to course")],
        )

    def test_item_type_summary_matches_total_items(self):
        summary = TI.item_type_summary()
        self.assertEqual(sum(summary.values()), len(TI.ITEMS))
        self.assertGreaterEqual(len(TI.ITEMS), 60)


if __name__ == "__main__":
    unittest.main()
