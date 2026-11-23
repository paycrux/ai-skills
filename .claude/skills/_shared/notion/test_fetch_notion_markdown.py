import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("fetch_notion_markdown.py")
INSTALL = "install: npm i -g @coastal-programs/notion-cli"
LOGIN = "login: notion-cli auth login"
PAGE = "https://www.notion.so/team/Spec-0123456789abcdef0123456789abcdef"

# A stand-in for @coastal-programs/notion-cli: knows `markdown get`, `whoami`; WHOAMI_FAIL=1 fakes a logged-out state.
COASTAL = """#!/bin/sh
case "$1 $2" in
  "markdown get") case "$*" in *--help*) exit 0;; *) echo "# Spec"; exit 0;; esac;;
  "whoami "*) [ -n "$WHOAMI_FAIL" ] && { echo "unauthorized" >&2; exit 1; }; echo ok; exit 0;;
esac
exit 2
"""
# The official Notion CLI has none of those commands.
OFFICIAL = "#!/bin/sh\necho 'unknown command' >&2\nexit 1\n"


class FetchNotionMarkdownTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, name, body):
        exe = self.bin / name
        exe.write_text(body)
        exe.chmod(0o755)

    def run_script(self, *args, **env):
        e = {**os.environ, "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin", **env}
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=e)

    def test_nothing_installed_prints_the_install_command(self):
        p = self.run_script("--check")
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn(INSTALL, p.stderr)

    def test_only_official_ntn_is_named_and_install_command_printed(self):
        self.tool("ntn", OFFICIAL)
        p = self.run_script(PAGE)
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn("ntn", p.stderr)
        self.assertIn(INSTALL, p.stderr)

    def test_a_different_tool_named_notion_cli_is_rejected(self):
        self.tool("notion-cli", OFFICIAL)
        p = self.run_script("--check")
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn(str(self.bin / "notion-cli"), p.stderr)
        self.assertIn(INSTALL, p.stderr)

    def test_logged_out_prints_the_login_command(self):
        self.tool("notion-cli", COASTAL)
        p = self.run_script("--check", WHOAMI_FAIL="1")
        self.assertEqual(p.returncode, 4, p.stderr)
        self.assertIn(LOGIN, p.stderr)

    def test_check_passes_when_installed_and_logged_in(self):
        self.tool("notion-cli", COASTAL)
        p = self.run_script("--check")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_fetch_still_prints_markdown(self):
        self.tool("notion-cli", COASTAL)
        p = self.run_script(PAGE, "--check-auth")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("# Spec", p.stdout)


if __name__ == "__main__":
    unittest.main()
