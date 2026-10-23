import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import unittest

BIN = os.path.join(os.path.dirname(__file__), "..", "bin", "co-nit")
loader = importlib.machinery.SourceFileLoader("co_nit", BIN)
spec = importlib.util.spec_from_loader("co_nit", loader)
co = importlib.util.module_from_spec(spec)
loader.exec_module(co)


class DvTest(unittest.TestCase):
    def test_known_nits(self):
        # Dynamia Soluciones (licence headers) and the DIAN itself
        self.assertEqual(co.dv("900302344"), 1)
        self.assertEqual(co.dv("800197268"), 4)

    def test_formatting_is_ignored(self):
        self.assertEqual(co.dv("900.302.344"), 1)
        self.assertEqual(co.dv(" 800 197 268 "), 4)

    def test_remainder_zero_or_one_is_the_dv(self):
        # find NITs by search so both branches are covered without trusting hand arithmetic
        seen = {co.dv(str(n)) for n in range(100000, 100200)}
        self.assertIn(0, seen)
        self.assertIn(1, seen)
        self.assertTrue(seen <= set(range(10)))

    def test_rejects_empty_and_too_long(self):
        with self.assertRaises(ValueError):
            co.dv("")
        with self.assertRaises(ValueError):
            co.dv("1" * 16)


class SplitCheckTest(unittest.TestCase):
    def test_split(self):
        self.assertEqual(co.split("900.302.344-1"), ("900302344", 1))
        self.assertEqual(co.split("900302344 - 1"), ("900302344", 1))
        self.assertEqual(co.split("900302344"), ("900302344", None))

    def test_split_rejects_text(self):
        with self.assertRaises(ValueError):
            co.split("abc")

    def test_check(self):
        self.assertTrue(co.check("900302344-1"))
        self.assertFalse(co.check("900302344-2"))
        with self.assertRaises(ValueError):
            co.check("900302344")


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, BIN, *args], capture_output=True, text=True)

    def test_dv(self):
        r = self.run_cli("dv", "800.197.268-4")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "4"))

    def test_check_ok_and_invalid(self):
        self.assertEqual(self.run_cli("check", "900302344-1").stdout.strip(), "ok")
        bad = self.run_cli("check", "900302344-9")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("expected DV 1", bad.stdout)

    def test_usage_and_errors_exit_2(self):
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("dv", "abc").returncode, 2)
        self.assertEqual(self.run_cli("check", "900302344").returncode, 2)


if __name__ == "__main__":
    unittest.main()
