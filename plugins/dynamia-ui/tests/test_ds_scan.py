import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

_KEEP = []
BIN = os.path.join(os.path.dirname(__file__), "..", "bin", "ds-scan")
loader = importlib.machinery.SourceFileLoader("ds_scan", BIN)
spec = importlib.util.spec_from_loader("ds_scan", loader)
ds = importlib.util.module_from_spec(spec)
loader.exec_module(ds)


def project(files):
    # keep the TemporaryDirectory alive for the test run: callers use `.name` on a temporary
    d = tempfile.TemporaryDirectory()
    _KEEP.append(d)
    for rel, text in files.items():
        p = os.path.join(d.name, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return d


class ScanTest(unittest.TestCase):
    def test_colors_raw_vs_defined(self):
        d = project({"a.css": ":root {\n  --brand: #FF0000;\n}\n.a { color: #f00; background: #00ff00; }\n"})
        r = ds.scan(d.name)
        self.assertEqual(r["colors"]["#ff0000"], {"raw": 1, "defined": 1})
        self.assertEqual(r["colors"]["#00ff00"], {"raw": 1, "defined": 0})

    def test_functional_colors_normalized(self):
        d = project({"a.css": ".a { color: rgba( 0, 0, 0, .5 ); }\n"})
        self.assertIn("rgba(0,0,0,.5)", ds.scan(d.name)["colors"])

    def test_href_anchor_is_not_a_color(self):
        d = project({"a.html": '<a href="#fee">x</a><i style="color:#abc">y</i>'})
        cols = ds.scan(d.name)["colors"]
        self.assertNotIn("#ffeeee", cols)
        self.assertIn("#aabbcc", cols)

    def test_tokens_unused(self):
        d = project({"a.css": ":root { --a: 1px; --b: 2px; }\n.x { margin: var(--a); }\n"})
        t = ds.scan(d.name)["tokens"]
        self.assertEqual(t["declared"], 2)
        self.assertEqual(t["unused"], ["--b"])

    def test_spacing_and_off_scale(self):
        d = project({"a.css": ".a { margin: 8px 13px; padding-left: 0; gap: 1.5rem; }\n"})
        r = ds.scan(d.name)
        self.assertEqual(r["spacing"], {"8px": 1, "13px": 1, "1.5rem": 1})
        self.assertEqual(r["off_scale_spacing"], {"13px": 1})

    def test_fonts_radius_shadow(self):
        css = ".a { font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 600;\n" \
              "border-radius: 4px  8px; box-shadow: 0 1px 2px #000; }\n"
        r = ds.scan(project({"a.css": css}).name)
        self.assertEqual(r["fonts"], {"Inter": 1})
        self.assertEqual(r["radius"], {"4px 8px": 1})
        self.assertEqual(r["font_sizes"], {"14px": 1})
        self.assertEqual(r["font_weights"], {"600": 1})
        self.assertEqual(len(r["shadows"]), 1)

    def test_tailwind_arbitrary(self):
        d = project({"a.vue": '<div class="p-[13px] mt-[1.5rem] w-full"></div>'})
        self.assertEqual(ds.scan(d.name)["arbitrary"], {"13px": 1, "1.5rem": 1})

    def test_near_duplicates(self):
        d = project({"a.css": ".a{color:#336699}.b{color:#346a9a}.c{color:#ff0000}"})
        self.assertEqual(ds.scan(d.name)["near_duplicates"], [["#336699", "#346a9a"]])

    def test_token_file_counts_as_defined(self):
        d = project({"tailwind.config.js": "module.exports={theme:{colors:{primary:'#112233'}}}"})
        r = ds.scan(d.name)
        self.assertEqual(r["colors"]["#112233"], {"raw": 0, "defined": 1})
        self.assertEqual(r["sources"], ["tailwind.config.js"])

    def test_stack_hints_from_package_json(self):
        pkg = json.dumps({"dependencies": {"vue": "^3"}, "devDependencies": {"tailwindcss": "^3"}})
        self.assertEqual(ds.scan(project({"package.json": pkg}).name)["stack_hints"], ["tailwind", "vue"])

    def test_skips_node_modules_and_minified(self):
        d = project({"node_modules/x/a.css": ".a{color:#111111}", "b.min.css": ".a{color:#222222}",
                     "c.css": ".a{color:#333333}"})
        self.assertEqual(list(ds.scan(d.name)["colors"]), ["#333333"])

    def test_invalid_package_json_is_ignored(self):
        self.assertEqual(ds.scan(project({"package.json": "{nope"}).name)["stack_hints"], [])


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, BIN, *args], capture_output=True, text=True)

    def test_missing_path_exits_2(self):
        r = self.run_cli("/nonexistent/path")
        self.assertEqual(r.returncode, 2)

    def test_json_output(self):
        d = project({"a.css": ".a{color:#abcdef}"})
        r = self.run_cli(d.name, "--json")
        self.assertEqual(r.returncode, 0)
        self.assertIn("#abcdef", json.loads(r.stdout)["colors"])

    def test_text_output(self):
        d = project({"a.css": ".a{color:#abcdef}"})
        r = self.run_cli(d.name)
        self.assertIn("#abcdef  raw x1", r.stdout)


if __name__ == "__main__":
    unittest.main()
