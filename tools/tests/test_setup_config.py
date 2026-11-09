# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for the written opencode config (no key on disk) and tools/run_opencode.py.

No secret store and no opencode program are used: both are replaced by fakes.
The fake key is built at run time so the secret scanner does not flag this file.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import opencode_config as oc  # noqa: E402
import run_opencode  # noqa: E402
import setup_nvidia  # noqa: E402
import setup_providers  # noqa: E402

FAKE_KEY = "nvapi-" + "Zz9" * 12


class TestNvidiaConfigStructure(unittest.TestCase):
    def setUp(self):
        self.models = setup_nvidia.parse_models(setup_nvidia.KB_XML)

    def test_parse_models_reads_api_ids(self):
        self.assertGreater(len(self.models), 0)
        by_alias = {m["alias"]: m for m in self.models}
        self.assertEqual(by_alias["mistral-large-4-1t-a52b"]["api_id"],
                         "mistralai/mistral-large-4-1t-a52b")

    def test_one_provider_in_providers_schema_without_key(self):
        config = setup_nvidia.update_config({"theme": "x"}, self.models)
        self.assertEqual(config["theme"], "x")
        self.assertEqual(list(config["providers"]), ["nvidia"])
        entry = config["providers"]["nvidia"]
        self.assertEqual(entry["package"], "@opencode/ai/providers/openai-compatible")
        self.assertEqual(entry["env"], ["NVIDIA_API_KEY"])
        self.assertEqual(entry["settings"], {"baseURL": "https://integrate.api.nvidia.com/v1"})
        self.assertEqual(len(entry["models"]), len(self.models))
        for model in entry["models"].values():
            self.assertEqual(set(model), {"modelID", "name"})
        self.assertEqual(oc.find_plaintext_keys(config), [])
        self.assertNotIn("chat/completions", json.dumps(config))

    def test_old_literal_key_and_apibase_removed_from_entry(self):
        old = {"providers": {"nvidia": {"settings": {"apiKey": FAKE_KEY, "apiBase": "x"}}}}
        config = setup_nvidia.update_config(old, self.models)
        self.assertNotIn(FAKE_KEY, json.dumps(config))
        self.assertEqual(config["providers"]["nvidia"]["settings"],
                         {"baseURL": "https://integrate.api.nvidia.com/v1"})


class TestProvidersConfigStructure(unittest.TestCase):
    def test_gemini_entry(self):
        config = setup_providers.update_config({}, "gemini")
        entry = config["providers"]["gemini"]
        self.assertEqual(entry["env"], ["GEMINI_API_KEY"])
        self.assertEqual(entry["package"], oc.OPENAI_COMPATIBLE)
        self.assertIn("baseURL", entry["settings"])
        self.assertNotIn("apiKey", entry["settings"])
        self.assertEqual(entry["models"]["gemini-3.8-flash"]["modelID"], "gemini-3.8-flash")

    def test_every_openai_compatible_provider_has_v1_style_base_url(self):
        for pid, spec in oc.PROVIDERS.items():
            with self.subTest(pid=pid):
                self.assertTrue(spec["env"].endswith("_API_KEY"))
                if spec["base_url"]:
                    self.assertTrue(spec["base_url"].startswith("https://"))
                    self.assertNotIn("chat/completions", spec["base_url"])

    def test_native_provider_is_not_written(self):
        with self.assertRaises(ValueError):
            oc.merge_provider({}, "openrouter", {})


class TestPlaintextKeyWarnings(unittest.TestCase):
    def test_find_reports_location_not_value(self):
        data = {"providers": {"a": {"settings": {"apiKey": FAKE_KEY}},
                              "b": {"settings": {"apiKey": "{env:B_API_KEY}"}}}}
        self.assertEqual(oc.find_plaintext_keys(data), ["providers.a.settings.apiKey"])

    def test_warn_never_prints_value_and_covers_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            body = json.dumps({"providers": {"x": {"settings": {"apiKey": FAKE_KEY}}}})
            path.write_text(body, encoding="utf-8")
            (Path(tmp) / "opencode.json.bak-20260101-000000").write_text(body, encoding="utf-8")
            out = io.StringIO()
            self.assertEqual(oc.warn_plaintext_keys(path, out), 2)
            self.assertNotIn(FAKE_KEY, out.getvalue())
            self.assertIn("plaintext", out.getvalue())

    def test_backup_redacts_literal_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text(json.dumps({"apiKey": FAKE_KEY, "theme": "t"}), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                saved = oc.write_json(path, {"theme": "t"})
            text = saved.read_text(encoding="utf-8")
            self.assertNotIn(FAKE_KEY, text)
            self.assertEqual(json.loads(text)["theme"], "t")
            self.assertEqual(oc.find_plaintext_keys(json.loads(text)), [])


class TestLauncher(unittest.TestCase):
    def fake_secret(self, key_path):
        if key_path == "nvidia/personal/api_key":
            return FAKE_KEY
        raise oc.ConfigError("not found", 1)

    def test_key_only_in_child_env_and_never_printed(self):
        calls = []

        def fake_run(cmd, env):
            calls.append((cmd, env))
            return mock.Mock(returncode=0)

        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"OPENCODE_CONFIG": str(Path(tmp) / "none.json")}), \
                mock.patch.object(sys, "stderr", err):
            os.environ.pop("NVIDIA_API_KEY", None)
            code = run_opencode.main(["run", "hi"], run=fake_run,
                                     which=lambda name: "/bin/opencode",
                                     get_secret=self.fake_secret)
            self.assertNotIn("NVIDIA_API_KEY", os.environ)
        self.assertEqual(code, 0)
        cmd, env = calls[0]
        self.assertEqual(cmd, ["/bin/opencode", "run", "hi"])
        self.assertEqual(env["NVIDIA_API_KEY"], FAKE_KEY)
        self.assertNotIn("GEMINI_API_KEY", env)
        self.assertNotIn(FAKE_KEY, err.getvalue())

    def test_only_limits_reads_and_existing_var_is_kept(self):
        asked = []

        def secret(path):
            asked.append(path)
            return FAKE_KEY

        env = run_opencode.child_env({"GEMINI_API_KEY": "mine"}, ["gemini", "nvidia"],
                                     secret, io.StringIO())
        self.assertEqual(asked, ["nvidia/personal/api_key"])
        self.assertEqual(env["GEMINI_API_KEY"], "mine")

    def test_missing_opencode(self):
        with mock.patch.object(sys, "stderr", io.StringIO()):
            code = run_opencode.main([], run=None, which=lambda name: None,
                                     get_secret=self.fake_secret)
        self.assertEqual(code, run_opencode.EXIT_NOT_FOUND)

    def test_unknown_only_provider(self):
        with mock.patch.object(sys, "stderr", io.StringIO()):
            self.assertEqual(run_opencode.main(["--only", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
