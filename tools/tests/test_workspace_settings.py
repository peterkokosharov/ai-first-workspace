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

    def test_kb_dir_defaults_to_kb_next_to_tools(self):
        self.assertEqual(ws.kb_dir({}), ws.ROOT / "kb")
        self.assertEqual(ws.kb_dir({"paths": {"kb": "   "}}), ws.ROOT / "kb")
        self.assertEqual(ws.kb_dir({"paths": {"kb": None}}), ws.ROOT / "kb")
        self.assertEqual(ws.kb_dir({"paths": "nonsense"}), ws.ROOT / "kb")

    def test_kb_dir_reads_relative_and_absolute_paths(self):
        self.assertEqual(ws.kb_dir({"paths": {"kb": "projects/models/kb"}}),
                         ws.ROOT / "projects" / "models" / "kb")
        absolute = Path(tempfile.gettempdir()) / "kb"
        self.assertEqual(ws.kb_dir({"paths": {"kb": str(absolute)}}), absolute)

    def test_example_has_a_paths_section(self):
        data = ws.load(ws.SETTINGS_EXAMPLE)
        self.assertEqual(data["paths"], {"kb": ""})

    def test_file_with_bom_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_bytes(b"\xef\xbb\xbf" + b'{"tools": {"git": "my-git"}}\n')
            self.assertEqual(ws.load(path), {"tools": {"git": "my-git"}})


class TestShippedModelList(unittest.TestCase):
    """A fresh clone has no kb/ and an empty paths.kb: the core's own list is used."""

    def test_fresh_settings_use_the_shipped_list(self):
        self.assertEqual(ws.models_xml({}), ws.ROOT / "data" / "models.xml")
        self.assertEqual(ws.models_xml({"paths": {"kb": ""}}), ws.ROOT / "data" / "models.xml")

    def test_setup_nvidia_finds_models_with_fresh_settings(self):
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        import opencode_config
        import setup_nvidia
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "opencode.json"
            out = io.StringIO()
            with mock.patch.object(ws, "load", return_value={}),                     mock.patch.object(setup_nvidia, "CONFIG_FILE", config),                     mock.patch.object(opencode_config, "stored_key_paths", return_value=set()),                     redirect_stdout(out):
                code = setup_nvidia.main(["--dry-run"])
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn("model(s) under providers.nvidia", out.getvalue())
            self.assertFalse(config.exists())
        models = setup_nvidia.parse_models(ws.ROOT / "data" / "models.xml")
        self.assertGreaterEqual(len(models), 20)
        self.assertTrue(all("/" in m["api_id"] for m in models))

    def test_a_models_xml_in_paths_kb_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "models.xml").write_text("<models/>", encoding="utf-8")
            self.assertEqual(ws.models_xml({"paths": {"kb": tmp}}), Path(tmp) / "models.xml")
            empty = Path(tmp) / "none"
            self.assertEqual(ws.models_xml({"paths": {"kb": str(empty)}}),
                             ws.ROOT / "data" / "models.xml")


if __name__ == "__main__":
    unittest.main()
