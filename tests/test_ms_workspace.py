"""Behavior tests for bin/ms-workspace and bin/ms-statusline (standard library only).

Run:  python3 -m unittest discover -s tests -v
Pick another implementation with MS_WORKSPACE_BIN=/path/to/ms-workspace.

Every test builds a throwaway workspace (bare remotes, clones on branch `next`) under a
temporary directory and a private HOME, so nothing outside it is touched.
"""
import base64
import json
import os
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BIN = os.environ.get("MS_WORKSPACE_BIN", str(REPO / "bin" / "ms-workspace"))
STATUSLINE = str(REPO / "bin" / "ms-statusline")

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

DEFAULT_TOML = """
name = "t"
[repos.lib]
base = "next"
deps = []
[repos.lib.test]
unit = "echo unit-lib"
affected = "echo affected {modules}"
[repos.app]
base = "next"
deps = ["lib"]
[repos.app.test]
unit = "echo unit-app"
"""


def run(cmd, cwd=None, env=None, input=None):
    return subprocess.run(cmd, cwd=cwd, env=env, input=input, text=True, capture_output=True)


class WS:
    """A temporary workspace with bare remotes and clones on branch `next`."""

    def __init__(self, repos=("lib", "app"), toml=DEFAULT_TOML):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()
        self.root = self.tmp / "ws"
        self.home = self.tmp / "home"
        self.cache = self.tmp / "cache"
        self.root.mkdir()
        self.home.mkdir()
        self.env = {
            **{k: v for k, v in os.environ.items() if not k.startswith(("MS_", "GIT_"))},
            "HOME": str(self.home),
            "MS_CACHE_DIR": str(self.cache),
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
        }
        self.env.pop("XDG_CACHE_HOME", None)
        for r in repos:
            remote = self.tmp / f"remote-{r}.git"
            self.git(self.tmp, "init", "-q", "--bare", str(remote))
            self.git(remote, "symbolic-ref", "HEAD", "refs/heads/next")
            self.git(self.tmp, "clone", "-q", str(remote), str(self.root / r))
            self.git(self.root / r, "checkout", "-q", "-b", "next")
            (self.root / r / "a.txt").write_text("base\n")
            self.commit(self.root / r, "init")
            self.git(self.root / r, "push", "-q", "origin", "next")
        if toml is not None:
            (self.root / "workspace.toml").write_text(textwrap.dedent(toml))

    def close(self):
        self._tmp.cleanup()

    def git(self, cwd, *args):
        r = run(["git", *args], cwd=cwd, env=self.env)
        if r.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {r.stderr}")
        return r.stdout.strip()

    def commit(self, cwd, msg, files=None):
        for name, content in (files or {}).items():
            p = Path(cwd) / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        self.git(cwd, "add", "-A")
        self.git(cwd, "commit", "-q", "-m", msg)

    def ms(self, *args, cwd=None, input=None, env=None):
        return run([BIN, *args], cwd=cwd or self.root, env={**self.env, **(env or {})}, input=input)

    def set_toml(self, text):
        (self.root / "workspace.toml").write_text(textwrap.dedent(text))

    def batch(self, name="b1", *repos):
        r = self.ms("batch", "new", name, *repos)
        assert r.returncode == 0, r.stderr
        return self.root / ".batches" / name

    def remote_log(self, repo, branch="next"):
        return self.git(self.tmp / f"remote-{repo}.git", "log", "--format=%s", branch).splitlines()

    def log_lines(self, *args):
        return self.ms("log", *args).stdout


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = WS()
        self.addCleanup(self.ws.close)

    def assertOk(self, r):
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout!r} stderr={r.stderr!r}")


# ---------------------------------------------------------------- batch / env
class TestBatch(Base):
    def test_batch_new_creates_worktrees_branches_and_tasks(self):
        d = self.ws.batch("b1")
        for r in ("lib", "app"):
            self.assertEqual(self.ws.git(d / r, "branch", "--show-current"), "int/b1")
        tasks = (d / "TASKS.md").read_text()
        self.assertIn("lib", tasks)
        self.assertIn("app", tasks)
        self.assertIn("batch.new", self.ws.log_lines())

    def test_batch_new_twice_fails(self):
        self.ws.batch("b1")
        r = self.ws.ms("batch", "new", "b1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stderr)

    def test_batch_new_subset_of_repos(self):
        d = self.ws.batch("b1", "lib")
        self.assertTrue((d / "lib").is_dir())
        self.assertFalse((d / "app").exists())

    def test_batch_new_unknown_repo_fails(self):
        r = self.ws.ms("batch", "new", "b1", "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nope", r.stderr)

    def test_batch_requires_workspace(self):
        r = self.ws.ms("batch", "new", "x", cwd=self.ws.tmp)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("workspace.toml", r.stderr)

    def test_env_copies_ignored_files_but_never_tracked_ones(self):
        lib = self.ws.root / "lib"
        (lib / ".gitignore").write_text(".env\nsecrets/*.json\nextra.env\n.claude/settings.local.json\n")
        (lib / ".worktreeinclude").write_text(".env\nsecrets/*.json\n")
        (lib / "tracked.txt").write_text("t")
        self.ws.commit(lib, "ignore rules")
        self.ws.git(lib, "push", "-q", "origin", "next")
        (lib / ".env").write_text("K=1\n")
        (lib / "secrets").mkdir()
        (lib / "secrets" / "a.json").write_text("{}")
        (lib / "extra.env").write_text("X=1\n")
        (lib / "not-ignored.txt").write_text("untracked and not ignored")
        (lib / ".claude").mkdir()
        (lib / ".claude" / "settings.local.json").write_text("{}")
        self.ws.set_toml(DEFAULT_TOML.replace('[repos.lib]\nbase = "next"', '[repos.lib]\nbase = "next"\nenv_files = ["extra.env"]'))
        d = self.ws.batch("b1", "lib")
        self.assertEqual((d / "lib" / ".env").read_text(), "K=1\n")
        self.assertTrue((d / "lib" / "secrets" / "a.json").exists())
        self.assertTrue((d / "lib" / "extra.env").exists())
        self.assertTrue((d / "lib" / ".claude" / "settings.local.json").exists())
        self.assertFalse((d / "lib" / "not-ignored.txt").exists())

    def test_env_setup_runs_the_configured_command(self):
        self.ws.set_toml(DEFAULT_TOML.replace('[repos.lib]\nbase = "next"', '[repos.lib]\nbase = "next"\nsetup = "echo hi > setup.out"'))
        d = self.ws.batch("b1", "lib")
        self.assertFalse((d / "lib" / "setup.out").exists())
        self.assertOk(self.ws.ms("env", "b1", "--setup"))
        self.assertEqual((d / "lib" / "setup.out").read_text().strip(), "hi")

    def test_env_trust_marks_worktrees_trusted(self):
        (self.ws.home / ".claude.json").write_text("{}")
        d = self.ws.batch("b1", "lib")
        self.assertOk(self.ws.ms("env", "b1", "--trust"))
        data = json.loads((self.ws.home / ".claude.json").read_text())
        self.assertTrue(data["projects"][str(d / "lib")]["hasTrustDialogAccepted"])

    def test_tasks_mode_per_repo(self):
        self.ws.set_toml(DEFAULT_TOML.replace('[repos.app]\nbase = "next"', '[repos.app]\nbase = "next"\ntasks = "github"'))
        tasks = (self.ws.batch("b1") / "TASKS.md").read_text()
        self.assertIn("- [ ] lib", tasks)
        self.assertIn("app: tracked in GitHub issues", tasks)


# ------------------------------------------------------------------- affected
class TestAffected(Base):
    def test_modules_and_dependents(self):
        d = self.ws.batch("b1")
        self.ws.commit(d / "lib", "mod", {"pom.xml": "<p/>", "m1/pom.xml": "<p/>", "m1/A.java": "x"})
        r = self.ws.ms("affected", cwd=d / "lib")
        self.assertOk(r)
        data = json.loads(r.stdout)
        self.assertEqual(data["repo"], "lib")
        self.assertIn("m1", data["modules"])
        self.assertEqual(data["dependents"], ["app"])

    def test_no_pom_means_no_modules(self):
        d = self.ws.batch("b1")
        self.ws.commit(d / "app", "x", {"f.txt": "x"})
        data = json.loads(self.ws.ms("affected", cwd=d / "app").stdout)
        self.assertEqual(data["modules"], [])
        self.assertEqual(data["dependents"], [])
        self.assertEqual(data["files"], 1)

    def test_outside_a_repo_fails(self):
        self.assertNotEqual(self.ws.ms("affected", cwd=self.ws.root).returncode, 0)


# ---------------------------------------------------------------------- tests
class TestRunner(Base):
    def test_t0_pass(self):
        d = self.ws.batch("b1")
        r = self.ws.ms("test", "t0", cwd=d / "lib")
        self.assertOk(r)
        self.assertIn("PASS t0 lib", r.stdout)

    def test_t0_fail_returns_code_and_shows_output(self):
        self.ws.set_toml(DEFAULT_TOML.replace('unit = "echo unit-lib"', 'unit = "echo boom-line; exit 3"'))
        d = self.ws.batch("b1")
        r = self.ws.ms("test", "t0", cwd=d / "lib")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL t0 lib", r.stderr)
        self.assertIn("boom-line", r.stderr)

    def test_memo_skips_identical_runs_until_code_changes(self):
        d = self.ws.batch("b1")
        wt = d / "lib"
        self.assertNotIn("cached", self.ws.ms("test", "t0", cwd=wt).stdout)
        self.assertIn("cached", self.ws.ms("test", "t0", cwd=wt).stdout)
        self.assertNotIn("cached", self.ws.ms("test", "t0", "--no-cache", cwd=wt).stdout)
        (wt / "new.txt").write_text("change")
        self.assertNotIn("cached", self.ws.ms("test", "t0", cwd=wt).stdout)

    def test_memo_is_not_written_for_failures(self):
        self.ws.set_toml(DEFAULT_TOML.replace('unit = "echo unit-lib"', 'unit = "exit 1"'))
        wt = self.ws.batch("b1") / "lib"
        self.assertNotEqual(self.ws.ms("test", "t0", cwd=wt).returncode, 0)
        self.assertNotIn("cached", self.ws.ms("test", "t0", cwd=wt).stdout)

    def test_memo_of_dependent_repo_sees_upstream_changes_in_batch(self):
        d = self.ws.batch("b1")
        self.assertNotIn("cached", self.ws.ms("test", "t0", cwd=d / "app").stdout)
        self.assertIn("cached", self.ws.ms("test", "t0", cwd=d / "app").stdout)
        self.ws.commit(d / "lib", "upstream change", {"u.txt": "x"})
        self.assertNotIn("cached", self.ws.ms("test", "t0", cwd=d / "app").stdout)

    def test_affected_command_receives_modules(self):
        d = self.ws.batch("b1")
        self.ws.commit(d / "lib", "mod", {"pom.xml": "<p/>", "m1/pom.xml": "<p/>", "m1/A.java": "x"})
        r = self.ws.ms("test", "t0", cwd=d / "lib")
        self.assertOk(r)
        self.assertRegex(r.stdout, r"affected .*m1")

    def test_t1_skips_unchanged_repos_and_adds_critical_modules(self):
        self.ws.set_toml(DEFAULT_TOML.replace('[repos.lib]\nbase = "next"', '[repos.lib]\nbase = "next"\ncritical = ["core"]'))
        d = self.ws.batch("b1")
        self.ws.commit(d / "lib", "mod", {"pom.xml": "<p/>", "m1/pom.xml": "<p/>", "m1/A.java": "x"})
        r = self.ws.ms("test", "t1", "b1")
        self.assertOk(r)
        self.assertIn("skip app", r.stdout)
        self.assertRegex(r.stdout, r"affected .*core")
        self.assertRegex(r.stdout, r"affected .*m1")

    def test_t1_stops_at_first_failing_repo(self):
        self.ws.set_toml(DEFAULT_TOML.replace('unit = "echo unit-lib"', 'unit = "exit 1"'))
        d = self.ws.batch("b1")
        self.ws.commit(d / "lib", "x", {"f.txt": "1"})
        self.ws.commit(d / "app", "x", {"f.txt": "1"})
        r = self.ws.ms("test", "t1", "b1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAIL t1 lib", r.stderr)
        self.assertNotIn("app", r.stdout)

    def test_t2_runs_e2e_command(self):
        self.ws.set_toml(DEFAULT_TOML + '\n[e2e]\ncommand = "echo e2e-ran"\nrepo = "app"\n')
        self.ws.batch("b1")
        r = self.ws.ms("test", "t2", "b1")
        self.assertOk(r)
        self.assertIn("PASS t2", r.stdout)

    def test_t2_without_config_fails(self):
        self.ws.batch("b1")
        self.assertNotEqual(self.ws.ms("test", "t2", "b1").returncode, 0)

    def test_unknown_level_fails(self):
        self.assertNotEqual(self.ws.ms("test", "t9").returncode, 0)


# ------------------------------------------------------ agents and integration
class TestIntegrate(Base):
    def setUp(self):
        super().setUp()
        self.d = self.ws.batch("b1")

    def agent(self, task, *repos):
        r = self.ws.ms("agent", "new", "b1", task, *repos)
        self.assertOk(r)
        return self.d / ".agents" / task

    def test_agent_new_creates_isolated_worktrees(self):
        a = self.agent("t1", "lib")
        self.assertEqual(self.ws.git(a / "lib", "branch", "--show-current"), "agent/b1/t1")
        self.assertFalse((a / "app").exists())

    def test_agent_new_duplicate_fails(self):
        self.agent("t1", "lib")
        self.assertNotEqual(self.ws.ms("agent", "new", "b1", "t1", "lib").returncode, 0)

    def test_dry_run_changes_nothing(self):
        a = self.agent("t1", "lib")
        self.ws.commit(a / "lib", "w", {"f1.txt": "1"})
        before = self.ws.git(self.d / "lib", "rev-parse", "HEAD")
        r = self.ws.ms("integrate", "b1", "--dry-run")
        self.assertOk(r)
        self.assertIn("merges cleanly", r.stdout)
        self.assertEqual(self.ws.git(self.d / "lib", "rev-parse", "HEAD"), before)

    def test_integrate_merges_all_agents_then_reports_already_merged(self):
        a1, a2 = self.agent("t1", "lib"), self.agent("t2", "lib", "app")
        self.ws.commit(a1 / "lib", "w1", {"f1.txt": "1"})
        self.ws.commit(a2 / "lib", "w2", {"f2.txt": "2"})
        self.ws.commit(a2 / "app", "w3", {"g.txt": "3"})
        r = self.ws.ms("integrate", "b1")
        self.assertOk(r)
        self.assertTrue((self.d / "lib" / "f1.txt").exists() and (self.d / "lib" / "f2.txt").exists())
        self.assertTrue((self.d / "app" / "g.txt").exists())
        self.assertIn("already merged", self.ws.ms("integrate", "b1").stdout)

    def test_conflict_reports_files_and_keeps_earlier_merges(self):
        a1, a2, a3 = self.agent("t1", "lib"), self.agent("t2", "lib"), self.agent("t3", "lib")
        self.ws.commit(a1 / "lib", "w1", {"ok.txt": "1"})
        self.ws.commit(a2 / "lib", "w2", {"clash.txt": "AAA"})
        self.ws.commit(a3 / "lib", "w3", {"clash.txt": "BBB"})
        r = self.ws.ms("integrate", "b1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CONFLICT", r.stderr)
        self.assertIn("clash.txt", r.stderr)
        self.assertTrue((self.d / "lib" / "ok.txt").exists())
        self.assertEqual(self.ws.git(self.d / "lib", "status", "--porcelain"), "")
        self.assertIn("conflict | integrate | lib | b1", self.ws.log_lines("--action", "integrate"))

    def test_dirty_integration_worktree_blocks_integrate(self):
        a = self.agent("t1", "lib")
        self.ws.commit(a / "lib", "w", {"f.txt": "1"})
        (self.d / "lib" / "dirty.txt").write_text("x")
        self.ws.git(self.d / "lib", "add", "dirty.txt")
        r = self.ws.ms("integrate", "b1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("uncommitted", r.stderr)

    def test_unknown_batch_fails(self):
        self.assertNotEqual(self.ws.ms("integrate", "ghost").returncode, 0)


# ----------------------------------------------------------------------- ship
class TestShip(Base):
    E2E = '\n[e2e]\ncommand = "echo e2e-ran"\nrepo = "app"\n'

    def setUp(self):
        super().setUp()
        self.ws.set_toml(DEFAULT_TOML + self.E2E)
        self.d = self.ws.batch("b1")
        self.ws.commit(self.d / "lib", "lib feature", {"feat.txt": "1"})
        self.ws.commit(self.d / "app", "app feature", {"feat.txt": "2"})

    def test_plan_only_does_not_push(self):
        r = self.ws.ms("ship", "b1")
        self.assertOk(r)
        self.assertIn("Plan for batch", r.stdout)
        self.assertIn("plan only", r.stdout)
        self.assertNotIn("lib feature", self.ws.remote_log("lib"))

    def test_yes_pushes_each_repo_to_its_base(self):
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertOk(r)
        self.assertIn("PASS t2", r.stdout)
        self.assertEqual(self.ws.remote_log("lib")[0], "lib feature")
        self.assertEqual(self.ws.remote_log("app")[0], "app feature")

    def test_missing_e2e_requires_explicit_skip(self):
        self.ws.set_toml(DEFAULT_TOML)
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--skip-e2e", r.stderr)
        self.assertNotIn("lib feature", self.ws.remote_log("lib"))
        self.assertOk(self.ws.ms("ship", "b1", "--yes", "--skip-e2e"))
        self.assertIn("lib feature", self.ws.remote_log("lib"))

    def test_failing_t1_blocks_the_push(self):
        self.ws.set_toml((DEFAULT_TOML + self.E2E).replace('unit = "echo unit-lib"', 'unit = "exit 1"'))
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("nothing was pushed", r.stderr)
        self.assertNotIn("lib feature", self.ws.remote_log("lib"))
        self.assertNotIn("app feature", self.ws.remote_log("app"))

    def test_failing_e2e_blocks_the_push(self):
        self.ws.set_toml(DEFAULT_TOML + '\n[e2e]\ncommand = "exit 1"\nrepo = "app"\n')
        self.assertNotEqual(self.ws.ms("ship", "b1", "--yes").returncode, 0)
        self.assertNotIn("lib feature", self.ws.remote_log("lib"))

    def test_base_moved_is_merged_before_pushing(self):
        mate = self.ws.tmp / "mate"
        self.ws.git(self.ws.tmp, "clone", "-q", str(self.ws.tmp / "remote-lib.git"), str(mate))
        self.ws.git(mate, "checkout", "-q", "next")
        self.ws.commit(mate, "mate commit", {"mate.txt": "m"})
        self.ws.git(mate, "push", "-q", "origin", "next")
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertOk(r)
        self.assertIn("base moved", r.stdout)
        log = self.ws.remote_log("lib")
        self.assertIn("mate commit", log)
        self.assertIn("lib feature", log)

    def test_release_branch_is_never_a_target(self):
        self.ws.set_toml((DEFAULT_TOML + self.E2E).replace('[repos.lib]\nbase = "next"', '[repos.lib]\nbase = "next"\nrelease = ["next"]'))
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("release branch", r.stderr)

    def test_dirty_worktree_blocks_ship(self):
        (self.d / "lib" / "feat.txt").write_text("changed again")
        r = self.ws.ms("ship", "b1", "--yes")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("uncommitted", r.stderr)

    def test_nothing_to_ship(self):
        self.ws.batch("empty")
        r = self.ws.ms("ship", "empty")
        self.assertOk(r)
        self.assertIn("Nothing to ship", r.stdout)

    def test_unknown_option_fails(self):
        self.assertNotEqual(self.ws.ms("ship", "b1", "--bogus").returncode, 0)


# ---------------------------------------------------------------------- clean
class TestClean(Base):
    def setUp(self):
        super().setUp()
        self.d = self.ws.batch("b1")
        self.ws.commit(self.d / "lib", "feature", {"f.txt": "1"})

    def test_list_shows_pending_then_merged(self):
        self.assertIn("b1: pending", self.ws.ms("clean").stdout)
        self.assertOk(self.ws.ms("ship", "b1", "--yes", "--skip-e2e"))
        self.assertIn("b1: merged", self.ws.ms("clean").stdout)

    def test_clean_refuses_unmerged_batches(self):
        r = self.ws.ms("clean", "b1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not merged", r.stderr)
        self.assertTrue(self.d.exists())

    def test_clean_after_ship_removes_worktrees_branches_and_dir(self):
        self.assertOk(self.ws.ms("agent", "new", "b1", "t1", "lib"))
        self.assertOk(self.ws.ms("ship", "b1", "--yes", "--skip-e2e"))
        self.assertOk(self.ws.ms("clean", "b1"))
        self.assertFalse(self.d.exists())
        branches = self.ws.git(self.ws.root / "lib", "branch", "--list")
        self.assertNotIn("int/b1", branches)
        self.assertNotIn("agent/b1/t1", branches)
        self.assertNotIn(".batches/b1", self.ws.git(self.ws.root / "lib", "worktree", "list"))

    def test_force_discards_unmerged_work(self):
        self.assertOk(self.ws.ms("clean", "b1", "--force"))
        self.assertFalse(self.d.exists())
        self.assertNotIn("int/b1", self.ws.git(self.ws.root / "lib", "branch", "--list"))

    def test_no_batches(self):
        w = WS()
        self.addCleanup(w.close)
        self.assertIn("no batches", w.ms("clean").stdout)


# ---------------------------------------------------------------------- guard
class TestGuard(Base):
    def guard(self, command, cwd):
        return self.ws.ms("guard", input=json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)}))

    def test_blocks_publishing_commands_inside_a_batch(self):
        d = self.ws.batch("b1")
        for cmd in ("git push origin int/b1", "git -C . push --force", "git push", "gh pr create --fill",
                    "gh pr merge 3", "ms-workspace ship b1 --yes", "ms-workspace clean b1"):
            with self.subTest(cmd=cmd):
                r = self.guard(cmd, d / "lib")
                self.assertEqual(r.returncode, 2, cmd)
                self.assertIn("Blocked", r.stderr)
        self.assertEqual(self.ws.log_lines("--action", "guard").count("blocked"), 7)

    def test_allows_normal_commands_inside_a_batch(self):
        d = self.ws.batch("b1")
        for cmd in ("git status", "git commit -m 'fix push handling'", "ms-workspace test t0", "ls"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.guard(cmd, d / "lib").returncode, 0, cmd)

    def test_allows_everything_outside_batches(self):
        self.ws.batch("b1")
        self.assertEqual(self.guard("git push origin next", self.ws.root / "lib").returncode, 0)

    def test_allows_everything_outside_a_workspace(self):
        self.assertEqual(self.guard("git push", self.ws.tmp).returncode, 0)

    def test_garbage_input_never_blocks(self):
        self.assertEqual(self.ws.ms("guard", input="not json").returncode, 0)
        self.assertEqual(self.ws.ms("guard", input="{}").returncode, 0)


# ------------------------------------------------- status / context / doctor
class TestOverview(Base):
    def test_status_one_line_per_repo(self):
        self.ws.batch("b1", "lib")
        lines = self.ws.ms("status").stdout.strip().splitlines()
        self.assertEqual(len(lines), 2)
        lib = next(l for l in lines if l.startswith("lib:"))
        self.assertIn("vs next: +0/-0", lib)
        self.assertIn("batches: b1", lib)
        self.assertNotIn("batches", next(l for l in lines if l.startswith("app:")))

    def test_status_reports_dirty_and_missing(self):
        (self.ws.root / "lib" / "x.txt").write_text("x")
        self.assertIn("dirty 1", self.ws.ms("status").stdout)
        self.ws.set_toml(DEFAULT_TOML + '\n[repos.ghost]\nbase = "next"\n')
        self.assertIn("ghost: (not cloned)", self.ws.ms("status").stdout)

    def test_context_briefing(self):
        out = self.ws.ms("context").stdout
        self.assertIn("Workspace 't'", out)
        self.assertIn("Active batches: none", out)
        self.ws.batch("b1")
        out = self.ws.ms("context").stdout
        self.assertIn("b1", out)
        self.assertIn("open tasks", out)
        self.assertIn("Recent actions", out)

    def test_context_is_silent_outside_a_workspace(self):
        r = self.ws.ms("context", cwd=self.ws.tmp)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_doctor_validates_workspace(self):
        out = self.ws.ms("doctor").stdout
        self.assertIn("all repos present, bases and deps valid", out)
        self.assertIn("Plan usage:", out)

    def test_doctor_flags_problems(self):
        self.ws.set_toml(DEFAULT_TOML.replace('deps = ["lib"]', 'deps = ["nobody"]'))
        r = self.ws.ms("doctor")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown repo 'nobody'", r.stdout)
        self.ws.set_toml(DEFAULT_TOML + '\n[repos.ghost]\nbase = "next"\n')
        r = self.ws.ms("doctor")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not cloned", r.stdout)

    def test_doctor_without_workspace_checks_general_tools(self):
        out = self.ws.ms("doctor", cwd=self.ws.tmp).stdout
        self.assertIn("general tools only", out)
        self.assertIn("git", out)

    def test_help_and_unknown_command(self):
        for flag in ("--help", "-h"):
            self.assertIn("batch new", self.ws.ms(flag, cwd=self.ws.tmp).stdout)
        r = self.ws.ms("frobnicate")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown command", r.stderr)


# ------------------------------------------------------------------ claude-md
class TestClaudeMd(Base):
    def test_create_content_and_order(self):
        r = self.ws.ms("claude-md")
        self.assertOk(r)
        text = (self.ws.root / "CLAUDE.md").read_text()
        self.assertIn("# Workspace: t", text)
        self.assertLess(text.index("- lib:"), text.index("- app:"))
        self.assertIn("depends on lib", text)
        self.assertIn("ms-workspace usage --check", text)
        self.assertIn("ms-agent-scout", text)
        self.assertEqual(text.count("ms-workspace:begin"), 1)

    def test_regeneration_keeps_user_notes_and_updates_block(self):
        self.ws.ms("claude-md")
        p = self.ws.root / "CLAUDE.md"
        p.write_text("# My notes\nkeep me\n\n" + p.read_text() + "\nfooter note\n")
        self.ws.set_toml(DEFAULT_TOML.replace('name = "t"', 'name = "renamed"'))
        self.assertIn("Updated", self.ws.ms("claude-md").stdout)
        text = p.read_text()
        self.assertIn("keep me", text)
        self.assertIn("footer note", text)
        self.assertIn("# Workspace: renamed", text)
        self.assertNotIn("# Workspace: t\n", text)
        self.assertEqual(text.count("ms-workspace:begin"), 1)

    def test_appends_block_to_an_existing_file_without_markers(self):
        p = self.ws.root / "CLAUDE.md"
        p.write_text("# Hand written\n")
        self.assertIn("Appended", self.ws.ms("claude-md").stdout)
        text = p.read_text()
        self.assertTrue(text.startswith("# Hand written"))
        self.assertIn("ms-workspace:end", text)

    def test_print_does_not_write(self):
        r = self.ws.ms("claude-md", "--print")
        self.assertIn("# Workspace: t", r.stdout)
        self.assertFalse((self.ws.root / "CLAUDE.md").exists())

    def test_tools_policy_and_task_overrides(self):
        self.ws.set_toml(DEFAULT_TOML.replace('name = "t"', 'name = "t"\ntasks = "local"\n[tools]\ndiscovery = ["idea", "mcp:ctx", "grep"]\nnotes = "Small diffs."')
                         .replace('[repos.app]\nbase = "next"', '[repos.app]\nbase = "next"\ntasks = "github"'))
        text = self.ws.ms("claude-md", "--print").stdout
        self.assertIn("1. IDE tools", text)
        self.assertIn("2. `mcp__ctx__*` tools", text)
        self.assertIn("3. Grep/Glob/Read", text)
        self.assertIn("Small diffs.", text)
        self.assertIn("- app: github", text)

    def test_default_tools_policy(self):
        text = self.ws.ms("claude-md", "--print").stdout
        self.assertIn("2. codebase-memory graph tools", text)
        self.assertIn("rtk", text)


# ---------------------------------------------------------------------- usage
class TestUsage(Base):
    def snapshot(self, p5, left5, p7=41.0, left7=4 * 86400, age=0):
        now = int(time.time())
        data = {"captured_at": now - age,
                "five_hour": None if p5 is None else {"used_percentage": p5, "resets_at": now + left5},
                "seven_day": {"used_percentage": p7, "resets_at": now + left7}}
        self.ws.cache.mkdir(exist_ok=True)
        (self.ws.cache / "usage.json").write_text(json.dumps(data))

    def check(self, *extra):
        return self.ws.ms("usage", "--check", *extra).returncode

    def test_exit_codes_by_scenario(self):
        cases = [
            (23, 4 * 3600, [], 0),          # early and low
            (55, 7200, [], 0),              # moderate, projection under 100
            (75, 7200, [], 1),              # above warn
            (92, 7200, [], 2),              # above stop
            (85, 9000, [], 2),              # runs out in under 30 min
            (23, 4 * 3600, ["--need", "30"], 0),
            (23, 4 * 3600, ["--need", "80"], 2),
            (60, 4 * 3600, ["--need", "35"], 1),
        ]
        for used, left, extra, expected in cases:
            with self.subTest(used=used, left=left, extra=extra):
                self.snapshot(used, left)
                self.assertEqual(self.check(*extra), expected)

    def test_no_data_is_exit_3_and_never_blocks_plain_calls(self):
        self.assertEqual(self.check(), 3)
        self.assertEqual(self.ws.ms("usage").returncode, 0)
        self.assertEqual(self.ws.ms("usage", "--line").returncode, 0)

    def test_expired_window_is_reported_as_reset(self):
        self.snapshot(80, -60)
        r = self.ws.ms("usage")
        self.assertIn("window reset", r.stdout)
        self.assertEqual(self.check(), 0)

    def test_text_json_and_line_outputs(self):
        self.snapshot(75, 7200)
        text = self.ws.ms("usage").stdout
        self.assertIn("75% used, 25% left", text)
        self.assertIn("verdict: WARN", text)
        data = json.loads(self.ws.ms("usage", "--json").stdout)
        self.assertEqual((data["verdict"], data["level"]), ("warn", 1))
        self.assertTrue(self.ws.ms("usage", "--line").stdout.startswith("usage 5h 75%"))

    def test_stale_data_is_noted(self):
        self.snapshot(23, 4 * 3600, age=3600)
        self.assertIn("min old", self.ws.ms("usage").stdout)

    def test_thresholds_come_from_workspace_toml(self):
        self.snapshot(40, 4 * 3600)
        self.assertEqual(self.check(), 0)
        self.ws.set_toml(DEFAULT_TOML + "\n[usage]\nwarn_pct = 30\nstop_pct = 35\n")
        self.assertEqual(self.check(), 2)

    def test_works_outside_a_workspace(self):
        self.snapshot(75, 7200)
        self.assertEqual(self.ws.ms("usage", "--check", cwd=self.ws.tmp).returncode, 1)

    def test_context_includes_a_usage_line(self):
        self.snapshot(23, 4 * 3600)
        self.assertIn("usage 5h 23%", self.ws.ms("context").stdout)

    def test_doctor_reports_the_snapshot(self):
        self.snapshot(23, 4 * 3600)
        self.assertIn("usage snapshot", self.ws.ms("doctor").stdout)


class TestStatusline(Base):
    def feed(self, **kw):
        now = int(time.time())
        payload = {"model": {"display_name": "Opus 5.5"}, "context_window": {"used_percentage": 12.4}}
        if kw:
            payload["rate_limits"] = {"five_hour": {"used_percentage": kw["p5"], "resets_at": now + 4 * 3600},
                                      "seven_day": {"used_percentage": kw["p7"], "resets_at": now + 4 * 86400}}
        return run([STATUSLINE], env=self.ws.env, input=json.dumps(payload))

    def test_prints_line_and_stores_snapshot_and_history(self):
        r = self.feed(p5=23.5, p7=41.2)
        self.assertEqual(r.returncode, 0)
        self.assertIn("[Opus 5.5] ctx 12%", r.stdout)
        self.assertIn("5h", r.stdout)
        self.assertIn("7d", r.stdout)
        snap = json.loads((self.ws.cache / "usage.json").read_text())
        self.assertEqual(snap["five_hour"]["used_percentage"], 23.5)
        self.assertEqual(snap["seven_day"]["used_percentage"], 41.2)
        self.assertEqual(len((self.ws.cache / "usage-history.jsonl").read_text().splitlines()), 1)
        self.feed(p5=24, p7=41.2)  # sampled at most once a minute
        self.assertEqual(len((self.ws.cache / "usage-history.jsonl").read_text().splitlines()), 1)

    def test_without_rate_limits_no_snapshot(self):
        r = self.feed()
        self.assertEqual(r.stdout.strip(), "[Opus 5.5] ctx 12%")
        self.assertFalse((self.ws.cache / "usage.json").exists())

    def test_garbage_input_is_harmless(self):
        r = run([STATUSLINE], env=self.ws.env, input="nonsense")
        self.assertEqual(r.returncode, 0)


# ------------------------------------------------------------------------ log
class TestLog(Base):
    def test_filters_and_limits(self):
        self.ws.batch("b1")
        self.ws.ms("test", "t0", cwd=self.ws.root / ".batches" / "b1" / "lib")
        self.assertIn("batch.new", self.ws.log_lines("--action", "batch.new"))
        self.assertNotIn("test.t0", self.ws.log_lines("--action", "batch.new"))
        self.assertEqual(len(self.ws.log_lines("-n", "1").strip().splitlines()), 1)
        today = time.strftime("%Y-%m-%d")
        self.assertIn("batch.new", self.ws.log_lines("--day", today))
        self.assertIn("no log for", self.ws.log_lines("--day", "1999-01-01"))

    def test_line_format(self):
        self.ws.batch("b1", "lib")
        line = self.ws.log_lines("-n", "1").strip()
        self.assertRegex(line, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d \| ok \| batch\.new \| lib \| b1 \| int/b1 from origin/next$")

    def test_empty_log(self):
        self.assertIn("no log yet", self.ws.log_lines())

    def test_old_daily_files_and_memos_are_rotated(self):
        logs = self.ws.root / ".ms-workspace" / "logs"
        memo = self.ws.root / ".ms-workspace" / "memo"
        logs.mkdir(parents=True)
        memo.mkdir()
        old = time.time() - 40 * 86400
        for p in (logs / "2020-01-01.jsonl", memo / "lib-abc"):
            p.write_text("{}\n")
            os.utime(p, (old, old))
        self.ws.batch("b1")
        self.assertFalse((logs / "2020-01-01.jsonl").exists())
        self.assertFalse((memo / "lib-abc").exists())

    def test_retention_is_configurable(self):
        self.ws.set_toml(DEFAULT_TOML.replace('name = "t"', 'name = "t"\nlog_retention_days = 100'))
        logs = self.ws.root / ".ms-workspace" / "logs"
        logs.mkdir(parents=True)
        old = time.time() - 40 * 86400
        (logs / "2020-01-01.jsonl").write_text("{}\n")
        os.utime(logs / "2020-01-01.jsonl", (old, old))
        self.ws.batch("b1")
        self.assertTrue((logs / "2020-01-01.jsonl").exists())


# --------------------------------------------------------------------- images
class TestImages(Base):
    def setUp(self):
        super().setUp()
        self.tp = self.ws.tmp / "transcript.jsonl"
        self.tp.write_text("")
        self.img_dir = self.ws.root / ".ms-workspace" / "images"

    def msg(self, text="hello\nworld  there", n=1, png=PNG, mt="image/png", ts="2026-10-15T23:40:00.000Z", role="user"):
        blocks = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(png).decode()}} for _ in range(n)]
        blocks.append({"type": "text", "text": text})
        return json.dumps({"type": role, "timestamp": ts, "cwd": str(self.ws.root / "lib"), "sessionId": "sess1234abcd",
                           "message": {"role": role, "content": blocks}})

    def capture(self, cwd=None, sid="sess1234abcd", tp=None):
        payload = {"transcript_path": str(tp or self.tp), "cwd": str(cwd or self.ws.root / "lib"), "session_id": sid}
        return self.ws.ms("images", "capture", input=json.dumps(payload))

    def files(self):
        return sorted(p for p in self.img_dir.rglob("*") if p.is_file() and p.suffix in (".png", ".jpg", ".gif", ".webp", ".bin"))

    def append(self, line):
        with open(self.tp, "a") as f:
            f.write(line)

    def test_saves_pasted_images_with_index(self):
        self.append(self.msg(n=1) + "\n")
        self.assertEqual(self.capture().returncode, 0)
        files = self.files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), PNG)
        self.assertRegex(files[0].name, r"^\d{6}_sess1234_1\.png$")
        entry = json.loads((self.img_dir / "index.jsonl").read_text().splitlines()[0])
        self.assertEqual(entry["text"], "hello world there")
        self.assertEqual(entry["media_type"], "image/png")
        self.assertEqual(entry["bytes"], len(PNG))
        self.assertIn("images", self.ws.log_lines("--action", "images"))

    def test_multiple_images_in_one_message_are_deduplicated_by_content(self):
        self.append(self.msg(n=2) + "\n")
        self.capture()
        self.assertEqual(len(self.files()), 1)

    def test_distinct_images_get_distinct_files(self):
        other = PNG + b"\x00"
        blocks = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(b).decode()}} for b in (PNG, other)]
        self.append(json.dumps({"timestamp": "2026-10-15T23:40:00.000Z", "cwd": "/x", "message": {"role": "user", "content": blocks}}) + "\n")
        self.capture()
        self.assertEqual([p.name[-6:] for p in self.files()], ["_1.png", "_2.png"])

    def test_incremental_reads_and_half_written_lines(self):
        self.append(self.msg(ts="2026-10-15T23:40:00.000Z") + "\n")
        self.capture()
        self.assertEqual(len(self.files()), 1)
        self.capture()
        self.assertEqual(len(self.files()), 1)
        second = self.msg(png=PNG + b"\x01", ts="2026-10-15T23:41:00.000Z")
        self.append(second[:80])
        self.capture()
        self.assertEqual(len(self.files()), 1, "a half-written line must wait")
        self.append(second[80:] + "\n")
        self.capture()
        self.assertEqual(len(self.files()), 2)

    def test_ignores_assistant_messages_and_tool_result_images(self):
        self.append(self.msg(role="assistant") + "\n")
        nested = {"timestamp": "2026-10-15T23:40:00.000Z", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "x", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(PNG).decode()}}]}]}}
        self.append(json.dumps(nested) + "\n")
        self.append("this line is not json\n")
        self.assertEqual(self.capture().returncode, 0)
        self.assertEqual(self.files(), [])

    def test_extension_follows_media_type(self):
        self.append(self.msg(mt="image/jpeg") + "\n")
        self.capture()
        self.assertTrue(self.files()[0].name.endswith(".jpg"))

    def test_capture_never_fails_the_session(self):
        for payload in ("", "garbage", "{}", json.dumps({"transcript_path": "/nope", "cwd": str(self.ws.root), "session_id": "s"})):
            self.assertEqual(self.ws.ms("images", "capture", input=payload).returncode, 0, payload)

    def test_outside_a_workspace_nothing_is_written(self):
        self.append(self.msg() + "\n")
        r = self.capture(cwd=self.ws.tmp)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.files(), [])

    def test_list_and_empty_state(self):
        self.assertIn("no images archived", self.ws.ms("images", "list").stdout)
        self.append(self.msg() + "\n")
        self.capture()
        out = self.ws.ms("images", "list").stdout
        self.assertIn("hello world there", out)
        self.assertIn(str(self.ws.root), out)
        self.assertIn("(0KB)", out)
        self.assertNotIn("\n\n", out.strip())
        self.assertEqual(self.ws.ms("images", "list", "--day", "1999-01-01").stdout.strip(), "")

    def test_default_subcommand_is_list(self):
        self.assertIn("no images archived", self.ws.ms("images").stdout)

    def test_backfill_imports_sessions_that_ran_inside_the_workspace(self):
        proj = self.ws.home / ".claude" / "projects" / "-x"
        proj.mkdir(parents=True)
        (proj / "inside.jsonl").write_text(self.msg(png=PNG + b"\x07") + "\n")
        outside = json.loads(self.msg(png=PNG + b"\x08"))
        outside["cwd"] = "/somewhere/else"
        (proj / "outside.jsonl").write_text(json.dumps(outside) + "\n")
        r = self.ws.ms("images", "backfill")
        self.assertOk(r)
        self.assertIn("Saved 1 image", r.stdout)
        self.assertEqual(len(self.files()), 1)

    def test_old_images_are_pruned_and_index_cleaned(self):
        self.ws.set_toml(DEFAULT_TOML.replace('name = "t"', 'name = "t"\nimages_retention_days = 5'))
        self.append(self.msg() + "\n")
        self.capture()
        f = self.files()[0]
        old = time.time() - 30 * 86400
        os.utime(f, (old, old))
        (self.img_dir / ".state" / ".pruned").unlink()
        self.append(self.msg(png=PNG + b"\x09", ts="2026-10-15T23:50:00.000Z") + "\n")
        self.capture()
        self.assertFalse(f.exists())
        index = [json.loads(l) for l in (self.img_dir / "index.jsonl").read_text().splitlines()]
        self.assertEqual(len(index), 1)
        self.assertTrue((self.ws.root / index[0]["file"]).exists())


# --------------------------------------------------------------------- memory
class TestMemory(Base):
    def add(self, *args, **kw):
        r = self.ws.ms("memory", "add", *args, **kw)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip().replace("saved ", "")

    def test_add_list_search_show_forget(self):
        name = self.add("--type", "gotcha", "--title", "Flaky port 8080", "The e2e stack needs port 8080 free.")
        self.add("--type", "decision", "We keep push direct on next because the team merges there.")
        out = self.ws.ms("memory", "list").stdout
        self.assertIn("gotcha", out)
        self.assertIn("Flaky port 8080", out)
        self.assertEqual(len(self.ws.ms("memory", "list", "--type", "decision").stdout.strip().splitlines()), 1)
        found = self.ws.ms("memory", "search", "PORT").stdout
        self.assertIn(name, found)
        self.assertIn("8080", found)
        self.assertIn("no matches", self.ws.ms("memory", "search", "nonexistent-term").stdout)
        shown = self.ws.ms("memory", "show", name).stdout
        self.assertIn("The e2e stack needs port 8080 free.", shown)
        self.assertIn("forgot", self.ws.ms("memory", "forget", name).stdout)
        self.assertNotIn("Flaky port 8080", self.ws.ms("memory", "list").stdout)

    def test_text_can_come_from_stdin(self):
        self.assertEqual(self.ws.ms("memory", "add", "--type", "lesson", input="multi\nline lesson\n").returncode, 0)
        self.assertIn("multi", self.ws.ms("memory", "list").stdout)

    def test_validation_and_empty_state(self):
        self.assertIn("no notes", self.ws.ms("memory", "list").stdout)
        self.assertNotEqual(self.ws.ms("memory", "add", "--type", "novel", "x").returncode, 0)
        self.assertNotEqual(self.ws.ms("memory", "add", "--type", "lesson", input="  ").returncode, 0)
        self.assertNotEqual(self.ws.ms("memory", "show", "ghost").returncode, 0)

    def test_ambiguous_reference_is_rejected(self):
        self.add("--title", "alpha one", "a")
        self.add("--title", "alpha two", "b")
        r = self.ws.ms("memory", "show", "alpha")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ambiguous", r.stderr)

    def test_context_shows_handoffs_of_active_batches_only(self):
        self.ws.batch("b1")
        self.add("--type", "handoff", "--batch", "b1", "Stopped after integrate; next run test t1 and ship.")
        self.add("--type", "handoff", "--batch", "gone", "Old batch handoff")
        self.add("--type", "gotcha", "--title", "Port clash", "x")
        ctx = self.ws.ms("context").stdout
        self.assertIn("Memory: 3 notes", ctx)
        self.assertIn("HANDOFF b1: Stopped after integrate", ctx)
        self.assertNotIn("HANDOFF gone", ctx)
        self.assertIn("Port clash", ctx)

    def test_cleaning_a_batch_drops_its_handoffs(self):
        d = self.ws.batch("b1")
        self.ws.commit(d / "lib", "f", {"f.txt": "1"})
        self.add("--type", "handoff", "--batch", "b1", "resume here")
        self.add("--type", "decision", "keep me")
        self.assertOk(self.ws.ms("ship", "b1", "--yes", "--skip-e2e"))
        self.assertOk(self.ws.ms("clean", "b1"))
        out = self.ws.ms("memory", "list").stdout
        self.assertNotIn("resume here", out)
        self.assertIn("keep me", out)

    def test_workspace_claude_md_tells_agents_about_memory(self):
        self.assertIn("memory add --type handoff", self.ws.ms("claude-md", "--print").stdout)


# ------------------------------------------------- log fields and insights
class TestInsights(Base):
    def snapshot(self, p5, p7=10.0):
        now = int(time.time())
        self.ws.cache.mkdir(exist_ok=True)
        (self.ws.cache / "usage.json").write_text(json.dumps({
            "captured_at": now, "five_hour": {"used_percentage": p5, "resets_at": now + 3 * 3600},
            "seven_day": {"used_percentage": p7, "resets_at": now + 4 * 86400}}))

    def events(self):
        out = []
        for f in sorted((self.ws.root / ".ms-workspace" / "logs").glob("*.jsonl")):
            out += [json.loads(l) for l in f.read_text().splitlines()]
        return out

    def write_events(self, rows):
        logs = self.ws.root / ".ms-workspace" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / f"{time.strftime('%Y-%m-%d')}.jsonl", "a") as fh:
            for r in rows:
                fh.write(json.dumps({"detail": "", "repo": "", **r}) + "\n")

    def test_test_events_carry_duration_and_code_key(self):
        wt = self.ws.batch("b1") / "lib"
        self.ws.ms("test", "t0", cwd=wt)
        ev = next(e for e in self.events() if e["action"] == "test.t0")
        self.assertIn("secs", ev)
        self.assertRegex(ev["key"], r"^[0-9a-f]{20}$")
        self.ws.ms("test", "t0", cwd=wt)
        self.assertTrue([e for e in self.events() if e["action"] == "test.t0"][-1]["cached"])

    def test_events_carry_plan_usage_when_a_fresh_snapshot_exists(self):
        self.snapshot(31.5, 12.0)
        self.ws.batch("b1", "lib")
        ev = next(e for e in self.events() if e["action"] == "batch.new")
        self.assertEqual((ev["u5"], ev["u7"]), (31.5, 12.0))

    def test_no_usage_fields_without_a_snapshot(self):
        self.ws.batch("b1", "lib")
        self.assertNotIn("u5", next(e for e in self.events() if e["action"] == "batch.new"))

    def test_flaky_candidate_same_code_fails_then_passes(self):
        flag = self.ws.tmp / "flag"
        self.ws.set_toml(DEFAULT_TOML.replace('unit = "echo unit-lib"', f'unit = "test -f {flag} || (touch {flag}; exit 1)"'))
        wt = self.ws.batch("b1") / "lib"
        self.assertNotEqual(self.ws.ms("test", "t0", cwd=wt).returncode, 0)
        self.assertEqual(self.ws.ms("test", "t0", cwd=wt).returncode, 0)
        data = json.loads(self.ws.ms("insights", "--json").stdout)
        self.assertEqual([f["repo"] for f in data["flaky"]], ["lib"])
        self.assertEqual((data["tests"]["lib"]["ok"], data["tests"]["lib"]["fail"]), (1, 1))
        self.assertIn("Flaky candidates", self.ws.ms("insights").stdout)

    def test_batch_cost_is_the_sum_of_usage_increases(self):
        self.snapshot(10)
        d = self.ws.batch("b1", "lib")
        self.snapshot(25)
        self.ws.ms("test", "t0", cwd=d / "lib")
        self.snapshot(5)   # a window reset must not count as negative cost
        self.ws.ms("test", "t0", "--no-cache", cwd=d / "lib")
        self.snapshot(9)
        self.ws.ms("test", "t0", "--no-cache", cwd=d / "lib")
        data = json.loads(self.ws.ms("insights", "--json").stdout)
        self.assertEqual(data["batches"]["b1"]["u5_cost"], 15.0 + 4.0)
        self.assertIn("of the 5h window", self.ws.ms("insights").stdout)

    def test_counts_guard_blocks_and_conflicts(self):
        d = self.ws.batch("b1")
        self.ws.ms("guard", input=json.dumps({"tool_input": {"command": "git push"}, "cwd": str(d / "lib")}))
        data = json.loads(self.ws.ms("insights", "--json").stdout)
        self.assertEqual(data["guard_blocks"], 1)

    def test_need_auto_uses_the_median_of_completed_batches(self):
        self.snapshot(20)
        rows = []
        for b, (lo, hi) in {"a": (0, 10), "b": (0, 20), "c": (0, 30)}.items():
            rows += [{"ts": f"2026-10-15T10:0{len(rows) % 9}:00-05:00", "action": "batch.new", "status": "ok", "batch": b, "u5": lo},
                     {"ts": f"2026-10-15T11:0{len(rows) % 9}:00-05:00", "action": "ship", "status": "ok", "batch": b, "u5": hi}]
        self.write_events(rows)
        out = self.ws.ms("usage", "--need", "auto").stdout
        self.assertIn("planned task: ~20% of the 5h window (median of 3 past batches)", out)
        self.assertIn("Typical completed batch", self.ws.ms("insights").stdout)

    def test_need_auto_refuses_without_history(self):
        self.snapshot(20)
        r = self.ws.ms("usage", "--need", "auto")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("history", r.stderr)
        self.assertNotEqual(self.ws.ms("usage", "--need", "auto", cwd=self.ws.tmp).returncode, 0)

    def test_empty_log(self):
        self.assertIn("0 logged actions", self.ws.ms("insights").stdout)


# ----------------------------------------------------------------- token audit
class TestTokens(Base):
    def assistant(self, mid, content, cwd, out=100, new=5, cache=1000, created=2000):
        return {"type": "assistant", "cwd": str(cwd), "timestamp": "2026-10-15T10:00:00.000Z", "sessionId": "s1",
                "message": {"id": mid, "role": "assistant", "model": "claude-sonnet-5-5", "content": content,
                            "usage": {"input_tokens": new, "cache_creation_input_tokens": created,
                                      "cache_read_input_tokens": cache, "output_tokens": out}}}

    def result(self, tool_id, chars, cwd):
        return {"type": "user", "cwd": str(cwd), "timestamp": "2026-10-15T10:00:05.000Z",
                "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": "x" * chars}]}}

    def session(self, name, rows, project="-proj"):
        d = self.ws.home / ".claude" / "projects" / project
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def read_block(self, tid, path):
        return {"type": "tool_use", "id": tid, "name": "Read", "input": {"file_path": path}}

    def test_totals_dedupe_repeated_message_lines_and_biggest_results(self):
        cwd = self.ws.root / ".batches" / "b1" / "lib"
        rows = [self.assistant("m1", [{"type": "thinking"}], cwd), self.assistant("m1", [self.read_block("t1", "/src/Big.java")], cwd),
                self.result("t1", 40000, cwd),
                self.assistant("m2", [{"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "ls"}}], cwd, out=50),
                self.result("t2", 400, cwd)]
        self.session("s1", rows)
        data = json.loads(self.ws.ms("tokens", "--json").stdout)
        self.assertEqual(data["sessions"], 1)
        self.assertEqual(data["total"]["requests"], 2, "the same message repeated per content block counts once")
        self.assertEqual(data["total"]["output"], 150)
        self.assertEqual(data["total"]["new_input"], 2 * (5 + 2000))
        self.assertEqual(data["total"]["cache_read"], 2000)
        self.assertIn("b1/lib", data["scopes"])
        self.assertEqual(data["biggest"][0]["tool"], "Read")
        self.assertEqual(data["biggest"][0]["approx_tokens"], 10000)
        self.assertEqual(data["tools"][0]["tool"], "Read")
        out = self.ws.ms("tokens").stdout
        self.assertIn("Token audit", out)
        self.assertIn("Hint: A single Read result", out)

    def test_repeated_reads_are_flagged(self):
        cwd = self.ws.root / "lib"
        rows = []
        for i in range(3):
            rows += [self.assistant(f"m{i}", [self.read_block(f"t{i}", "/src/Same.java")], cwd), self.result(f"t{i}", 100, cwd)]
        self.session("s2", rows)
        data = json.loads(self.ws.ms("tokens", "--json").stdout)
        self.assertEqual(data["repeated_reads"][0]["reads"], 3)
        self.assertIn("read 3 times", self.ws.ms("tokens").stdout)

    def test_sessions_outside_the_workspace_are_ignored(self):
        self.session("s3", [self.assistant("m1", [{"type": "text", "text": "hi"}], self.ws.tmp / "elsewhere")])
        self.assertIn("No Claude Code sessions", self.ws.ms("tokens").stdout)

    def test_old_sessions_are_ignored(self):
        self.session("s4", [self.assistant("m1", [{"type": "text", "text": "hi"}], self.ws.root / "lib")])
        f = self.ws.home / ".claude" / "projects" / "-proj" / "s4.jsonl"
        old = time.time() - 30 * 86400
        os.utime(f, (old, old))
        self.assertIn("No Claude Code sessions", self.ws.ms("tokens").stdout)
        self.assertEqual(json.loads(self.ws.ms("tokens", "--days", "60", "--json").stdout)["sessions"], 1)

    def test_agent_worktree_scope(self):
        cwd = self.ws.root / ".batches" / "b1" / ".agents" / "t1" / "lib"
        self.session("s5", [self.assistant("m1", [{"type": "text", "text": "hi"}], cwd)])
        self.assertIn("b1/lib", json.loads(self.ws.ms("tokens", "--json").stdout)["scopes"])


# ----------------------------------------------------------- hooks / settings
class TestSetupHooks(Base):
    def setUp(self):
        super().setUp()
        self.home = self.ws.tmp / "claude-home"
        self.settings = self.home / "settings.json"
        self.env = {"CLAUDE_HOME": str(self.home)}

    def setup(self, *args):
        return self.ws.ms("setup-hooks", *args, cwd=self.ws.tmp, env=self.env)

    def load(self):
        return json.loads(self.settings.read_text())

    def commands(self, data):
        return [h["command"] for groups in data.get("hooks", {}).values() for g in groups for h in g["hooks"]]

    def test_dry_run_changes_nothing(self):
        r = self.setup("--dry-run")
        self.assertOk(r)
        self.assertIn("dry run", r.stdout)
        self.assertIn("added", r.stdout)
        self.assertFalse(self.settings.exists())

    def test_fresh_install_adds_everything_once(self):
        self.assertOk(self.setup())
        data = self.load()
        cmds = self.commands(data)
        for c in ("ms-workspace guard", "ms-workspace context", "ms-workspace images capture"):
            self.assertIn(c, cmds)
        self.assertEqual(data["statusLine"]["command"], "ms-statusline")
        self.assertIn("Bash(ms-workspace:*)", data["permissions"]["allow"])
        before = self.settings.read_text()
        r = self.setup()
        self.assertIn("Already up to date", r.stdout)
        self.assertEqual(self.settings.read_text(), before)
        for event, groups in self.load()["hooks"].items():
            per_event = [h["command"] for g in groups for h in g["hooks"]]
            self.assertEqual(len(per_event), len(set(per_event)), event)

    def test_existing_settings_are_preserved_and_backed_up(self):
        self.home.mkdir()
        existing = {"model": "opus", "statusLine": {"type": "command", "command": "my-line"},
                    "permissions": {"allow": ["Bash(ls:*)"], "deny": ["Bash(rm:*)"]},
                    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]},
                                              {"matcher": "Grep|Glob", "hooks": [{"type": "command", "command": "gate"}]}]}}
        self.settings.write_text(json.dumps(existing))
        r = self.setup()
        self.assertOk(r)
        self.assertIn("backup:", r.stdout)
        self.assertIn("kept     statusLine", r.stdout)
        data = self.load()
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["statusLine"]["command"], "my-line", "another status line is never overwritten")
        self.assertEqual(data["permissions"]["deny"], ["Bash(rm:*)"])
        self.assertEqual(data["permissions"]["allow"][0], "Bash(ls:*)")
        bash_group = next(g for g in data["hooks"]["PreToolUse"] if g["matcher"] == "Bash")
        self.assertEqual([h["command"] for h in bash_group["hooks"]], ["rtk hook claude", "ms-workspace guard"])
        self.assertIn("gate", self.commands(data))
        self.assertEqual(len(list(self.home.glob("settings.json.bak-*"))), 1)

    def test_remove_only_takes_out_what_we_added(self):
        self.home.mkdir()
        self.settings.write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]}]}}))
        self.setup()
        r = self.setup("--remove")
        self.assertOk(r)
        self.assertIn("removed", r.stdout)
        data = self.load()
        self.assertEqual(self.commands(data), ["rtk hook claude"])
        self.assertNotIn("statusLine", data)
        self.assertNotIn("Bash(ms-workspace:*)", data.get("permissions", {}).get("allow", []))
        self.assertIn("Nothing to remove", self.setup("--remove").stdout)

    def test_invalid_json_is_never_overwritten(self):
        self.home.mkdir()
        self.settings.write_text("{ not json")
        r = self.setup()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.settings.read_text(), "{ not json")

    def test_project_scope_writes_to_the_project_settings(self):
        proj = self.ws.tmp / "proj"
        proj.mkdir()
        r = self.ws.ms("setup-hooks", "--project", cwd=proj, env=self.env)
        self.assertOk(r)
        self.assertTrue((proj / ".claude" / "settings.json").exists())
        self.assertFalse(self.settings.exists())

    def test_doctor_checks_the_hooks(self):
        env = {"CLAUDE_HOME": str(self.home)}
        before = self.ws.ms("doctor", env=env).stdout
        self.assertIn("not installed in settings.json", before)
        self.setup()
        self.assertIn("hooks are installed", self.ws.ms("doctor", env=env).stdout)


# ------------------------------------------------------------------ packaging
class TestPackaging(unittest.TestCase):
    """Skills and agents are plain files that Claude Code parses as YAML frontmatter; a stray ': ' breaks them."""

    def frontmatter(self, path):
        text = path.read_text()
        self.assertTrue(text.startswith("---\n"), f"{path}: missing frontmatter")
        head = text[4:].split("\n---\n", 1)[0]
        fields = {}
        for line in head.splitlines():
            if line.startswith((" ", "-")) or ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        return fields

    def test_skills_have_valid_frontmatter(self):
        skills = sorted((REPO / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 8)
        for path in skills:
            with self.subTest(skill=path.parent.name):
                f = self.frontmatter(path)
                self.assertEqual(f.get("name"), path.parent.name)
                self.assertTrue(f.get("description"))
                for key, value in f.items():
                    if value and value[0] not in "\"'[{>|":
                        self.assertNotIn(": ", value, f"{key} has an unquoted ': ' (invalid YAML)")
                        self.assertNotIn(" #", value, f"{key} has an unquoted ' #' (YAML comment)")

    def test_agents_have_valid_frontmatter_and_the_prefix(self):
        for path in sorted((REPO / "agents").glob("*.md")):
            with self.subTest(agent=path.stem):
                f = self.frontmatter(path)
                self.assertEqual(f.get("name"), path.stem)
                self.assertTrue(path.stem.startswith("ms-agent-"))
                self.assertIn(f.get("model"), ("haiku", "sonnet", "opus"))
                self.assertTrue(f.get("description"))
                for key, value in f.items():
                    if value and value[0] not in "\"'[{>|":
                        self.assertNotIn(": ", value, f"{key} has an unquoted ': ' (invalid YAML)")

    def test_settings_example_is_valid_and_complete(self):
        data = json.loads((REPO / "settings" / "hooks.example.json").read_text())
        cmds = {h["command"] for groups in data["hooks"].values() for g in groups for h in g["hooks"]}
        self.assertEqual(cmds, {"ms-workspace guard", "ms-workspace context", "ms-workspace images capture"})
        self.assertEqual(data["statusLine"]["command"], "ms-statusline")

    def test_example_workspace_config_parses(self):
        import tomllib
        cfg = tomllib.loads((REPO / "skills" / "ms-workspace-init" / "references" / "workspace.example.toml").read_text())
        self.assertIn("repos", cfg)

    def test_installer_links_everything_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "CLAUDE_HOME": f"{tmp}/c", "BIN_DIR": f"{tmp}/b"}
            first = run([str(REPO / "install.sh")], env=env)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue((Path(tmp) / "b" / "ms-workspace").is_symlink())
            self.assertTrue((Path(tmp) / "c" / "skills" / "ms-ship").is_symlink())
            self.assertTrue((Path(tmp) / "c" / "agents" / "ms-agent-boss.md").is_symlink())
            self.assertTrue((Path(tmp) / "c" / "CLAUDE.md").is_symlink())
            second = run([str(REPO / "install.sh")], env=env)
            self.assertNotIn("backup", second.stdout)
            dry = run([str(REPO / "install.sh"), "--uninstall"], env=env)
            self.assertFalse((Path(tmp) / "b" / "ms-workspace").exists())
            self.assertEqual(dry.returncode, 0)


if __name__ == "__main__":
    unittest.main()
