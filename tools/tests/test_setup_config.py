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
NVIDIA_STORED = {"nvidia/personal/api_key"}


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
        config = setup_nvidia.update_config(old, self.models, stored=NVIDIA_STORED)
        self.assertNotIn(FAKE_KEY, json.dumps(config))
        self.assertEqual(config["providers"]["nvidia"]["settings"],
                         {"baseURL": "https://integrate.api.nvidia.com/v1"})


OLD_NVIDIA_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"


def old_nvidia_config(aliases, key=FAKE_KEY):
    """The exact shape the old setup_nvidia.py (78d4c37) wrote: one entry per model."""
    return {"theme": "t", "providers": {
        alias: {"settings": {"apiKey": key, "apiBase": OLD_NVIDIA_ENDPOINT},
                "models": {alias: {"modelID": f"nvidia/{alias}", "name": alias.upper()}}}
        for alias in aliases}}


class TestLegacyCleanup(unittest.TestCase):
    def setUp(self):
        self.models = setup_nvidia.parse_models(setup_nvidia.KB_XML)
        self.aliases = [m["alias"] for m in self.models]

    def test_old_per_alias_entries_removed(self):
        notes = []
        config = setup_nvidia.update_config(old_nvidia_config(self.aliases[:3]), self.models, notes,
                                            stored=NVIDIA_STORED)
        self.assertEqual(list(config["providers"]), ["nvidia"])
        self.assertNotIn(FAKE_KEY, json.dumps(config))
        self.assertEqual(oc.find_plaintext_keys(config), [])
        self.assertEqual(config["theme"], "t")
        self.assertEqual(len(notes), 3)
        self.assertTrue(all("already in the OS store" in n for n in notes))
        self.assertNotIn(FAKE_KEY, "".join(notes))

    def test_old_entry_found_by_api_base_even_if_alias_unknown(self):
        old = old_nvidia_config(["model-gone-from-xml"])
        config = setup_nvidia.update_config(old, self.models, stored=NVIDIA_STORED)
        self.assertNotIn("model-gone-from-xml", config["providers"])
        self.assertNotIn(FAKE_KEY, json.dumps(config))

    def test_only_the_exact_old_endpoint_marks_a_legacy_entry(self):
        config = {"providers": {"mine": {"settings": {
            "apiBase": "https://integrate.api.nvidia.com/v1", "apiKey": "{env:MINE}"}}}}
        self.assertEqual(oc.clean_legacy(config, stored=NVIDIA_STORED), [])
        self.assertIn("mine", config["providers"])

    def test_legacy_key_not_in_store_is_kept_with_set_command(self):
        old = old_nvidia_config(self.aliases[:2])
        notes, warnings = [], []
        config = setup_nvidia.update_config(old, self.models, notes, stored=set(),
                                            warnings=warnings)
        self.assertEqual(notes, [])
        for alias in self.aliases[:2]:
            self.assertEqual(config["providers"][alias]["settings"]["apiKey"], FAKE_KEY)
        self.assertEqual(len(warnings), 2)
        for warning in warnings:
            self.assertIn("python3 tools/secret.py set nvidia/personal/api_key", warning)
            self.assertNotIn(FAKE_KEY, warning)

    def test_managed_key_not_in_store_is_kept(self):
        old = {"providers": {"gemini": {"settings": {"apiKey": FAKE_KEY}}}}
        warnings = []
        config = setup_nvidia.update_config(old, self.models, stored=NVIDIA_STORED,
                                            warnings=warnings)
        self.assertEqual(config["providers"]["gemini"]["settings"]["apiKey"], FAKE_KEY)
        self.assertEqual(len(warnings), 1)
        self.assertIn("secret.py set gemini/personal/api_key", warnings[0])

    def test_nvidia_entry_key_kept_through_merge_when_not_stored(self):
        old = {"providers": {"nvidia": {"settings": {"apiKey": FAKE_KEY}}}}
        warnings = []
        config = setup_nvidia.update_config(old, self.models, stored=set(), warnings=warnings)
        self.assertEqual(config["providers"]["nvidia"]["settings"]["apiKey"], FAKE_KEY)
        self.assertEqual(config["providers"]["nvidia"]["env"], ["NVIDIA_API_KEY"])
        self.assertEqual(len(warnings), 1)

    def test_non_dict_providers_or_entries_are_left_alone(self):
        for providers in ([], "x", None, 3):
            with self.subTest(providers=providers):
                config = {"providers": providers}
                self.assertEqual(oc.clean_legacy(config, self.aliases, NVIDIA_STORED), [])
                self.assertEqual(config, {"providers": providers})
        config = {"providers": {self.aliases[0]: "text", "gemini": ["a"], "x": None}}
        self.assertEqual(oc.clean_legacy(config, self.aliases, NVIDIA_STORED), [])
        self.assertEqual(config["providers"],
                         {self.aliases[0]: "text", "gemini": ["a"], "x": None})

    def test_foreign_key_kept_and_warned_by_default(self):
        config = {"providers": {"mine": {"settings": {"apiKey": FAKE_KEY, "baseURL": "https://x"},
                                         "models": {"m": {"modelID": "m", "name": "M"}}}}}
        notes, warnings = [], []
        setup_nvidia.update_config(config, self.models, notes, stored=NVIDIA_STORED,
                                   warnings=warnings)
        self.assertEqual(config["providers"]["mine"]["settings"]["apiKey"], FAKE_KEY)
        self.assertEqual(notes, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("providers.mine.settings.apiKey", warnings[0])
        self.assertIn("--redact-foreign", warnings[0])
        self.assertNotIn(FAKE_KEY, warnings[0])

    def test_foreign_key_redacted_only_with_flag(self):
        config = {"providers": {"mine": {"settings": {"apiKey": FAKE_KEY, "baseURL": "https://x"}},
                                "gemini": {"settings": {"apiKey": FAKE_KEY}}}}
        notes, warnings = [], []
        setup_nvidia.update_config(config, self.models, notes, stored=NVIDIA_STORED,
                                   redact_foreign=True, warnings=warnings)
        self.assertEqual(config["providers"]["mine"]["settings"]["apiKey"], oc.REDACTED)
        self.assertEqual(config["providers"]["mine"]["settings"]["baseURL"], "https://x")
        # A managed key that is not in the store is not "foreign": still kept.
        self.assertEqual(config["providers"]["gemini"]["settings"]["apiKey"], FAKE_KEY)
        self.assertEqual(len(notes), 1)
        self.assertIn("providers.mine.settings.apiKey", notes[0])
        self.assertEqual(len(warnings), 1)

    def test_env_reference_is_not_touched(self):
        config = {"providers": {"mine": {"settings": {"apiKey": "{env:MINE_API_KEY}"}}}}
        self.assertEqual(oc.clean_legacy(config), [])
        self.assertEqual(config["providers"]["mine"]["settings"]["apiKey"], "{env:MINE_API_KEY}")

    def test_old_setup_providers_shape_cleaned(self):
        # Old setup_providers.py (78d4c37): providers.<id>.settings.apiKey = real key.
        old = {"providers": {"gemini": {"settings": {"apiKey": FAKE_KEY}, "models": {
            "gemini-3.8-flash": {"modelID": "gemini/gemini-3.8-flash", "name": "Gemini 3.8 Flash"}}}}}
        notes = []
        config = setup_providers.update_config(old, "gemini", notes,
                                               stored={"gemini/personal/api_key"})
        self.assertNotIn(FAKE_KEY, json.dumps(config))
        self.assertEqual(notes, ["providers.gemini.settings.apiKey (plaintext key, already in "
                                 "the OS store) removed"])
        self.assertEqual(config["providers"]["gemini"]["env"], ["GEMINI_API_KEY"])
        out = io.StringIO()
        oc.report_cleaned(notes, out=out)
        self.assertIn("may differ from the stored key", out.getvalue())
        self.assertIn("backup", out.getvalue())
        self.assertNotIn(FAKE_KEY, out.getvalue())

    def test_native_provider_old_key_removed_and_file_written(self):
        old = {"providers": {"openrouter": {"settings": {"apiKey": FAKE_KEY}}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text(json.dumps(old), encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(setup_providers, "CONFIG_FILE", path), \
                    mock.patch.object(setup_providers, "get_key_from_secret", return_value="x"), \
                    mock.patch.object(oc, "stored_key_paths", return_value=None), \
                    mock.patch.object(oc, "warn_plaintext_keys", return_value=0), \
                    redirect_stdout(out):
                code = setup_providers.configure_provider("openrouter")
            self.assertEqual(code, 0)
            self.assertNotIn(FAKE_KEY, path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["providers"], {})
            self.assertIn("cleaned: providers.openrouter.settings.apiKey", out.getvalue())
            self.assertNotIn(FAKE_KEY, out.getvalue())

    def test_native_provider_clean_config_not_rewritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text('{"theme": "t"}', encoding="utf-8")
            with mock.patch.object(setup_providers, "CONFIG_FILE", path), \
                    mock.patch.object(setup_providers, "get_key_from_secret", return_value="x"), \
                    mock.patch.object(oc, "stored_key_paths", return_value=set()), \
                    mock.patch.object(oc, "warn_plaintext_keys", return_value=0), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(setup_providers.configure_provider("openrouter"), 0)
            self.assertEqual([f.name for f in Path(tmp).iterdir()], ["opencode.json"])

    def test_write_opencode_config_cleans_file_and_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            body = json.dumps(old_nvidia_config(self.aliases[:2]))
            path.write_text(body, encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(setup_nvidia, "CONFIG_FILE", path), \
                    mock.patch.object(sys, "stderr", io.StringIO()), redirect_stdout(out):
                setup_nvidia.write_opencode_config(self.models, stored=NVIDIA_STORED)
            backups = list(Path(tmp).glob("opencode.json.bak-*"))
            self.assertEqual(len(list(Path(tmp).iterdir())), 2)  # config + one backup
            self.assertEqual(backups[0].read_text(encoding="utf-8"), body)  # exact copy
            self.assertNotIn(FAKE_KEY, path.read_text(encoding="utf-8"))
            self.assertEqual(list(json.loads(path.read_text(encoding="utf-8"))["providers"]),
                             ["nvidia"])
            self.assertIn(f"cleaned: providers.{self.aliases[0]}", out.getvalue())
            self.assertNotIn(FAKE_KEY, out.getvalue())

    def test_dry_run_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            body = json.dumps(old_nvidia_config(self.aliases[:1]))
            path.write_text(body, encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(setup_nvidia, "CONFIG_FILE", path), \
                    mock.patch.object(sys, "stderr", io.StringIO()), redirect_stdout(out):
                setup_nvidia.write_opencode_config(self.models, dry_run=True,
                                                   stored=NVIDIA_STORED)
            self.assertEqual(path.read_text(encoding="utf-8"), body)
            self.assertIn("would clean:", out.getvalue())

    def test_setup_nvidia_main_checks_store_before_cleaning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            body = json.dumps(old_nvidia_config(self.aliases[:1]))
            path.write_text(body, encoding="utf-8")
            out = io.StringIO()
            calls = []

            def stored():
                calls.append("listed")
                return set()

            with mock.patch.object(setup_nvidia, "CONFIG_FILE", path), \
                    mock.patch.object(oc, "stored_key_paths", side_effect=stored), \
                    mock.patch.object(setup_nvidia, "get_key_from_secret",
                                      side_effect=AssertionError("no value read")), \
                    mock.patch.object(sys, "stderr", io.StringIO()), redirect_stdout(out):
                self.assertEqual(setup_nvidia.main([]), 0)
            self.assertEqual(calls, ["listed"])
            text = out.getvalue()
            self.assertLess(text.index("not in the OS secret store"), text.index("warning:"))
            self.assertIn("python3 tools/secret.py set nvidia/personal/api_key", text)
            self.assertNotIn(FAKE_KEY, text)
            # Key not stored: it stays in the config; the backup is an exact copy.
            self.assertIn(FAKE_KEY, path.read_text(encoding="utf-8"))

    def test_setup_providers_keeps_other_unstored_keys(self):
        old = {"providers": {"nvidia": {"settings": {"apiKey": FAKE_KEY}},
                             "gemini": {"settings": {"apiKey": FAKE_KEY}}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text(json.dumps(old), encoding="utf-8")
            out = io.StringIO()
            with mock.patch.object(setup_providers, "CONFIG_FILE", path), \
                    mock.patch.object(setup_providers, "get_key_from_secret", return_value="x"), \
                    mock.patch.object(oc, "stored_key_paths", return_value=set()), \
                    mock.patch.object(oc, "warn_plaintext_keys", return_value=0), \
                    redirect_stdout(out):
                self.assertEqual(setup_providers.configure_provider("gemini"), 0)
            providers = json.loads(path.read_text(encoding="utf-8"))["providers"]
            self.assertNotIn("apiKey", providers["gemini"]["settings"])  # checked: stored
            self.assertEqual(providers["nvidia"]["settings"]["apiKey"], FAKE_KEY)  # not stored
            self.assertIn("secret.py set nvidia/personal/api_key", out.getvalue())
            self.assertNotIn(FAKE_KEY, out.getvalue())


class TestStoredKeyPaths(unittest.TestCase):
    def test_lists_names_only(self):
        result = mock.Mock(returncode=0, stdout='["a/b/c", "nvidia/personal/api_key"]')
        with mock.patch.object(oc.subprocess, "run", return_value=result) as run:
            self.assertEqual(oc.stored_key_paths(), {"a/b/c", "nvidia/personal/api_key"})
        argv = run.call_args.args[0]
        self.assertEqual(argv[-2:], ["list", "--json"])
        self.assertNotIn("get", argv)

    def test_failure_means_unknown(self):
        for result in (mock.Mock(returncode=2, stdout=""), mock.Mock(returncode=0, stdout="x"),
                       mock.Mock(returncode=0, stdout='{"a": 1}')):
            with self.subTest(result=result), \
                    mock.patch.object(oc.subprocess, "run", return_value=result):
                self.assertIsNone(oc.stored_key_paths())
        with mock.patch.object(oc.subprocess, "run", side_effect=OSError("gone")):
            self.assertIsNone(oc.stored_key_paths())


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

    def test_project_level_config_in_current_dir_is_checked(self):
        with tempfile.TemporaryDirectory() as glob_dir, tempfile.TemporaryDirectory() as proj:
            body = json.dumps({"providers": {"x": {"settings": {"apiKey": FAKE_KEY}}}})
            (Path(proj) / "opencode.jsonc").write_text(body, encoding="utf-8")
            out = io.StringIO()
            found = oc.warn_plaintext_keys(Path(glob_dir) / "opencode.json", out, Path(proj))
            self.assertEqual(found, 1)
            self.assertIn("opencode.jsonc", out.getvalue())
            self.assertNotIn(FAKE_KEY, out.getvalue())

    def test_project_level_default_is_current_dir(self):
        with tempfile.TemporaryDirectory() as glob_dir, tempfile.TemporaryDirectory() as proj:
            (Path(proj) / "opencode.json").write_text(json.dumps({"apiKey": FAKE_KEY}),
                                                      encoding="utf-8")
            old_cwd = os.getcwd()
            os.chdir(proj)
            try:
                found = oc.warn_plaintext_keys(Path(glob_dir) / "opencode.json", io.StringIO())
            finally:
                os.chdir(old_cwd)
            self.assertEqual(found, 1)

    def test_project_file_equal_to_global_counted_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text(json.dumps({"apiKey": FAKE_KEY}), encoding="utf-8")
            self.assertEqual(oc.warn_plaintext_keys(path, io.StringIO(), Path(tmp)), 1)

    def test_backup_is_exact_copy_and_warns_without_value(self):
        # The backup may be the only copy of a key that is not in the store yet.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            body = json.dumps({"apiKey": FAKE_KEY, "theme": "t"}).encode()
            path.write_bytes(body)
            out = io.StringIO()
            with redirect_stdout(out):
                saved = oc.write_json(path, {"theme": "t"})
            self.assertEqual(saved.read_bytes(), body)
            self.assertIn("exact copy", out.getvalue())
            self.assertIn("Delete it by hand", out.getvalue())
            self.assertNotIn(FAKE_KEY, out.getvalue())
            if os.name == "posix":
                self.assertEqual(saved.stat().st_mode & 0o777, 0o600)


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

    def run_main(self, argv, which, run=None):
        calls = []

        def fake_run(cmd, env):
            calls.append(cmd)
            return mock.Mock(returncode=0)

        err = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"OPENCODE_CONFIG": str(Path(tmp) / "none.json")}), \
                mock.patch.object(sys, "stderr", err):
            code = run_opencode.main(argv, run=run or fake_run, which=which,
                                     get_secret=self.fake_secret)
        return code, calls, err.getvalue()

    def test_only_parsing(self):
        cases = {
            ("--only", "nvidia", "run"): (["nvidia"], ["run"]),
            ("--only=gemini,nvidia",): (["gemini", "nvidia"], []),
            ("run", "--only", "x"): (None, ["run", "--only", "x"]),
            ("--onlyx",): (None, ["--onlyx"]),
        }
        for argv, (want, rest) in cases.items():
            with self.subTest(argv=argv):
                args = list(argv)
                self.assertEqual(run_opencode.parse_only(args), (want, None))
                self.assertEqual(args, rest)

    def test_bare_only_is_an_error(self):
        for argv in (["--only"], ["--only="], ["--only", "--help"], ["--only", ","]):
            with self.subTest(argv=argv):
                code, calls, err = self.run_main(argv, which=lambda name: "/bin/opencode")
                self.assertEqual(code, 2)
                self.assertEqual(calls, [])
                self.assertIn("--only needs a value", err)

    def test_prefers_exe_next_to_cmd_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim = Path(tmp) / "opencode.cmd"
            exe = Path(tmp) / "opencode.exe"
            shim.write_text("", encoding="utf-8")
            exe.write_text("", encoding="utf-8")
            self.assertEqual(run_opencode.find_opencode(lambda name: str(shim)), str(exe))

    def test_prefers_exe_on_path_over_cmd_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim = str(Path(tmp) / "opencode.CMD")
            which = {"opencode": shim, "opencode.exe": "/other/opencode.exe"}.get
            self.assertEqual(run_opencode.find_opencode(which), "/other/opencode.exe")

    def test_cmd_shim_refuses_cmd_metacharacters(self):
        which = {"opencode": "C:/npm-missing/opencode.cmd"}.get
        for arg in ("a & calc", "x|y", "^", "100%", "<in", ">out", 'say "hi"', "hi!",
                    "a\nb", "a\rb"):
            with self.subTest(arg=arg):
                code, calls, err = self.run_main(["run", arg], which=which)
                self.assertEqual(code, 2)
                self.assertEqual(calls, [])
                self.assertIn("batch file", err)

    def test_cmd_shim_runs_plain_args(self):
        which = {"opencode": "C:/npm-missing/opencode.bat"}.get
        code, calls, _ = self.run_main(["run", "-m", "nvidia/x", "hello world"], which=which)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [["C:/npm-missing/opencode.bat", "run", "-m", "nvidia/x",
                                  "hello world"]])

    def test_exe_passes_metacharacters(self):
        code, calls, _ = self.run_main(["run", "a & b"], which=lambda name: "/bin/opencode")
        self.assertEqual(code, 0)
        self.assertEqual(calls, [["/bin/opencode", "run", "a & b"]])

    def test_sigint_not_default_while_child_runs_and_restored(self):
        import signal
        before = signal.getsignal(signal.SIGINT)
        seen = []

        def fake_run(cmd, env):
            handler = signal.getsignal(signal.SIGINT)
            seen.append(handler)
            handler(signal.SIGINT, None)  # a Ctrl+C now must not raise in the launcher
            return mock.Mock(returncode=0)

        code, _, _ = self.run_main([], which=lambda name: "/bin/opencode", run=fake_run)
        self.assertEqual(code, 0)
        self.assertTrue(callable(seen[0]))
        self.assertNotIn(seen[0], (signal.default_int_handler, before))
        self.assertIs(signal.getsignal(signal.SIGINT), before)

    def test_sigint_handler_restored_when_run_raises(self):
        import signal
        before = signal.getsignal(signal.SIGINT)
        for exc, expected in ((OSError(2, "No such file"), run_opencode.EXIT_NOT_FOUND),
                              (KeyboardInterrupt(), 130)):
            with self.subTest(exc=type(exc).__name__):
                def failing_run(cmd, env, exc=exc):
                    raise exc

                code, _, _ = self.run_main([], which=lambda name: "/bin/opencode",
                                           run=failing_run)
                self.assertEqual(code, expected)
                self.assertIs(signal.getsignal(signal.SIGINT), before)


if __name__ == "__main__":
    unittest.main()
