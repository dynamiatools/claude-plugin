"""Tests for skills/powers-installers/scripts/powers.sh (standard library only).

Every test uses a private HOME and fake curl/uv/graphify commands, so nothing is
downloaded or installed.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/powers-installers/scripts/powers.sh"


class TestPowers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.stubs = self.home / "stubs"
        self.stubs.mkdir()
        self.calls = self.home / "calls.log"
        self.addCleanup(self.tmp.cleanup)

    def stub(self, name, body):
        p = self.stubs / name
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(0o755)

    def run_powers(self, *args):
        env = {"HOME": str(self.home), "PATH": f"{self.stubs}:/usr/bin:/bin", "CALLS": str(self.calls)}
        return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env)

    def calls_made(self):
        return self.calls.read_text() if self.calls.exists() else ""

    def test_plan_without_yes_runs_nothing(self):
        self.stub("uv", 'echo "uv $*" >> "$CALLS"\n')
        r = self.run_powers("install", "graphify")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("would    install package: uv tool install graphifyy", r.stdout)
        self.assertEqual(self.calls_made(), "")

    def test_missing_prerequisite_fails(self):
        r = self.run_powers("install", "headroom")
        self.assertEqual(r.returncode, 1)
        self.assertIn("needs 'uv'", r.stderr)

    def test_unknown_tool_is_rejected(self):
        r = self.run_powers("install", "nope", "--yes")
        self.assertEqual(r.returncode, 2)

    def test_yes_runs_install_steps_in_order(self):
        self.stub("uv", 'echo "uv $*" >> "$CALLS"\n')
        self.stub("graphify", 'echo "graphify $*" >> "$CALLS"\n')
        # graphify is already on PATH here, so use remove to exercise --yes
        r = self.run_powers("remove", "graphify", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.calls_made().splitlines(), ["graphify uninstall", "uv tool uninstall graphifyy"])

    def test_remote_script_is_downloaded_hashed_then_run(self):
        self.stub("curl", 'out=""; while [ $# -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done\n'
                          'printf "echo ran >> \\"$CALLS\\"\\n" > "$out"\n')
        r = self.run_powers("install", "uv", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"sha256   [0-9a-f]{64}")
        self.assertEqual(self.calls_made().strip(), "ran")

    def test_failed_download_reports_failure(self):
        self.stub("curl", "exit 22\n")
        r = self.run_powers("install", "uv", "--yes")
        self.assertEqual(r.returncode, 1)
        self.assertIn("download failed", r.stderr)

    def test_list_marks_installed(self):
        self.stub("rtk", "echo rtk 1.0\n")
        r = self.run_powers("list")
        self.assertRegex(r.stdout, r"rtk\s+installed")
        self.assertRegex(r.stdout, r"uv\s+missing")


if __name__ == "__main__":
    unittest.main()
