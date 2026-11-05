import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import scanner  # noqa: E402


CLEAN = {"available": True, "status": "clean", "infected": False}
ERROR = {"available": True, "status": "error", "infected": False, "reason": "timeout"}
UNAVAILABLE = {"available": False, "status": "unavailable", "infected": False, "reason": "nao instalado"}
SKIPPED = {"available": True, "status": "skipped", "infected": False, "reason": "arquivo grande"}
INFECTED = {"available": True, "status": "infected", "infected": True, "signature": "Sig.Test"}


class ScanContractTests(unittest.TestCase):
    def _scan(self, clam, yara):
        with patch.object(scanner, "scan_with_clamav", return_value=clam), patch.object(
            scanner, "scan_with_yara", return_value=yara
        ):
            return scanner.scan_file("arquivo.bin")

    def test_both_clean_is_complete(self):
        result = self._scan(CLEAN, CLEAN)
        self.assertTrue(result["complete"])
        self.assertFalse(result["infected"])
        self.assertEqual(result["summary"], "Limpo")
        self.assertEqual(result["warnings"], [])
        self.assertNotIn("error", result)

    def test_clamav_error_with_yara_clean_is_partial(self):
        result = self._scan(ERROR, CLEAN)
        self.assertFalse(result["complete"])
        self.assertFalse(result["infected"])
        self.assertTrue(any("ClamAV" in w for w in result["warnings"]))
        self.assertTrue(result["summary"].startswith("Parcial"))
        self.assertNotIn("error", result)

    def test_clamav_skipped_is_partial(self):
        result = self._scan(SKIPPED, CLEAN)
        self.assertFalse(result["complete"])
        self.assertTrue(any("ignorado" in w for w in result["warnings"]))

    def test_engine_unavailable_is_partial(self):
        result = self._scan(UNAVAILABLE, CLEAN)
        self.assertFalse(result["complete"])
        self.assertTrue(any("indisponivel" in w for w in result["warnings"]))

    def test_yara_infected_is_complete_and_reported(self):
        result = self._scan(CLEAN, INFECTED)
        self.assertTrue(result["complete"])
        self.assertTrue(result["infected"])
        self.assertIn("YARA:Sig.Test", result["signatures"])

    def test_infected_with_engine_error_is_partial(self):
        result = self._scan(ERROR, INFECTED)
        self.assertFalse(result["complete"])
        self.assertTrue(result["infected"])
        self.assertTrue(result["summary"].endswith("(parcial)"))

    def test_no_engine_available_sets_error(self):
        result = self._scan(UNAVAILABLE, UNAVAILABLE)
        self.assertFalse(result["complete"])
        self.assertIn("error", result)
        self.assertIn("Nenhum engine", result["error"])

    def test_all_engines_errored_sets_error(self):
        result = self._scan(ERROR, ERROR)
        self.assertFalse(result["complete"])
        self.assertIn("error", result)


class RuleSelectionTests(unittest.TestCase):
    def test_prefers_installed_full_over_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "yara", "rules"))
            full = os.path.join(tmp, "yara", "rules", "full.yar")
            fallback = os.path.join(tmp, "yara", "fallback.yar")
            Path(full).write_text("rule Full { condition: true }", encoding="utf-8")
            Path(fallback).write_text("rule Fallback { condition: true }", encoding="utf-8")
            with patch.object(scanner, "get_bundle_base", return_value=tmp), patch.object(
                scanner, "get_exe_dir", return_value=tmp
            ), patch.object(scanner.os, "getcwd", return_value=tmp):
                self.assertEqual(scanner.find_yara_rules(), full)

    def test_compiled_rules_must_be_newer_than_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            rules = os.path.join(tmp, "full.yar")
            compiled = os.path.join(tmp, "full.yarc")
            Path(rules).write_text("rule X { condition: true }", encoding="utf-8")
            Path(compiled).write_bytes(b"compiled")
            os.utime(rules, (1000, 1000))
            os.utime(compiled, (2000, 2000))
            self.assertEqual(scanner.find_yara_compiled(rules), compiled)
            os.utime(compiled, (500, 500))
            self.assertIsNone(scanner.find_yara_compiled(rules))

    def test_scan_uses_compiled_rules(self):
        with patch.object(scanner, "find_yara", return_value="yara64.exe"), patch.object(
            scanner, "find_yara_rules", return_value="rules.yar"
        ), patch.object(
            scanner, "find_yara_compiled", return_value="rules.yarc"
        ), patch.object(
            scanner.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ) as run:
            result = scanner.scan_with_yara("arquivo.bin")
        self.assertEqual(run.call_args[0][0][:3], ["yara64.exe", "-C", "rules.yarc"])
        self.assertEqual(result["status"], "clean")

    def test_scan_uses_source_when_no_compiled_rules(self):
        with patch.object(scanner, "find_yara", return_value="yara64.exe"), patch.object(
            scanner, "find_yara_rules", return_value="rules.yar"
        ), patch.object(
            scanner, "find_yara_compiled", return_value=None
        ), patch.object(
            scanner.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ) as run:
            scanner.scan_with_yara("arquivo.bin")
        self.assertEqual(run.call_args[0][0][:2], ["yara64.exe", "rules.yar"])


class ClamAVLimitTests(unittest.TestCase):
    def test_large_file_is_skipped_without_subprocess(self):
        with patch.object(scanner, "find_clamscan", return_value="clamscan.exe"), patch.object(
            scanner.os.path, "getsize", return_value=scanner.CLAMAV_MAX_BYTES + 1
        ):
            result = scanner.scan_with_clamav("grande.bin")
        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["infected"])
        self.assertIn("limite", result["reason"])

    def test_missing_binary_is_unavailable(self):
        with patch.object(scanner, "find_clamscan", return_value=None):
            result = scanner.scan_with_clamav("x.bin")
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["available"])

    def test_missing_yara_rules_is_error(self):
        with patch.object(scanner, "find_yara", return_value="yara64.exe"), patch.object(
            scanner, "find_yara_rules", return_value=None
        ):
            result = scanner.scan_with_yara("x.bin")
        self.assertEqual(result["status"], "error")
        self.assertIn("regras", result["reason"])


if __name__ == "__main__":
    unittest.main()
