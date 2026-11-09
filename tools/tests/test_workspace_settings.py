# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for tools/workspace_settings.py (temp files only; the real settings.json is
never read or written)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import workspace_settings as ws  # noqa: E402


class TestWorkspaceSettings(unittest.TestCase):
    def test_example_has_git_and_tools_sections(self):
        data = ws.load(ws.SETTINGS_EXAMPLE)
        self.assertEqual(ws.git_settings(data),
                         {"remote_url": "", "remote_user": "",
                          "token_key": "personal/my-project/github_token"})
        for name in ("python", "git", "bash", "node", "opencode", "merman", "docker"):
            self.assertEqual(data["tools"][name], "")

    def test_empty_tool_means_default_name(self):
        data = {"tools": {"opencode": ""}}
        self.assertEqual(ws.configured_tool("opencode", data), "")
        self.assertEqual(ws.tool_command("opencode", data), "opencode")

    def test_tools_wins_over_runtime(self):
        data = {"runtime": {"opencode": "old-oc", "git": "rt-git"},
                "tools": {"opencode": "/new/oc", "git": ""}}
        self.assertEqual(ws.tool_command("opencode", data), "/new/oc")
        self.assertEqual(ws.tool_command("git", data), "rt-git")  # old key still works

    def test_all_commands_has_defaults_and_extra_names(self):
        commands = ws.all_commands({"runtime": {"custom": "c"}})
        self.assertEqual(commands["npm"], "npm")
        self.assertEqual(commands["custom"], "c")

    def test_missing_or_broken_file_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ws.load(Path(tmp) / "none.json"), {})
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            self.assertEqual(ws.load(bad), {})
            listed = Path(tmp) / "list.json"
            listed.write_text(json.dumps([1, 2]), encoding="utf-8")
            self.assertEqual(ws.load(listed), {})
            self.assertEqual(ws.git_settings({}),
                             {"remote_url": "", "remote_user": "", "token_key": ""})

    def test_file_with_bom_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_bytes(b"\xef\xbb\xbf" + b'{"tools": {"git": "my-git"}}\n')
            self.assertEqual(ws.load(path), {"tools": {"git": "my-git"}})


if __name__ == "__main__":
    unittest.main()
