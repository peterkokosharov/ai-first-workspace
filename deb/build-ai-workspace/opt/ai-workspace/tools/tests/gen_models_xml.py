#!/usr/bin/env python3
"""Functional tests for tools/gen_models_xml.py.

Tests index parsing, Python code generation and XML building using
temporary files. No network calls are made.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SUT = Path(__file__).resolve().parents[1] / "gen_models_xml.py"  # tools/gen_models_xml.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("gen_models_xml_sut", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gmx = _load_sut()


class TestParseIndex(unittest.TestCase):
    """Parsing of free_endpoints_index.md table rows."""

    def test_parse_valid_rows(self):
        content = (
            "| # | Alias | Full Name | Vendor | Endpoint | Tags | Source |\n"
            "|---|-------|-----------|--------|----------|------|--------|\n"
            "| 1 | mistralai/mistral-large-4-1t-a52b | Mistral Large 4 | NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions | Chat | source |\n"
            "| 2 | nvidia/nemotron-3.5-bolt-e4b | Nemotron Bolt | NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions | Agent | source |\n"
            "| 3 | explore/discover | Try NVIDIA NIM APIs | NVIDIA | None | Agent | source |\n"
        )
        path = Path(self.tmp) / "index.md"
        path.write_text(content, encoding="utf-8")
        models = gmx.parse_index(path)

        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["alias"], "mistral-large-4-1t-a52b")
        self.assertEqual(models[0]["full_alias"], "mistralai/mistral-large-4-1t-a52b")
        self.assertEqual(models[0]["endpoint"], "https://integrate.api.nvidia.com/v1/chat/completions")
        self.assertEqual(models[1]["alias"], "nemotron-3.5-bolt-e4b")
        self.assertEqual(models[1]["full_alias"], "nvidia/nemotron-3.5-bolt-e4b")

    def test_parse_skips_none_endpoint(self):
        content = (
            "| # | Alias | Full Name | Vendor | Endpoint | Tags | Source |\n"
            "|---|-------|-----------|--------|----------|------|--------|\n"
            "| 1 | nvidia/some-model | Some Model | NVIDIA | None | Agent | source |\n"
        )
        path = Path(self.tmp) / "index.md"
        path.write_text(content, encoding="utf-8")
        models = gmx.parse_index(path)
        self.assertEqual(len(models), 0)

    def test_parse_skips_explore_discover(self):
        content = (
            "| # | Alias | Full Name | Vendor | Endpoint | Tags | Source |\n"
            "|---|-------|-----------|--------|----------|------|--------|\n"
            "| 1 | explore/discover | Try NVIDIA NIM APIs | NVIDIA | https://integrate.api.nvidia.com/v1/chat/completions | Agent | source |\n"
        )
        path = Path(self.tmp) / "index.md"
        path.write_text(content, encoding="utf-8")
        models = gmx.parse_index(path)
        self.assertEqual(len(models), 0)

    def test_parse_empty_input(self):
        path = Path(self.tmp) / "index.md"
        path.write_text("", encoding="utf-8")
        models = gmx.parse_index(path)
        self.assertEqual(models, [])

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gen_models_xml_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestPythonCodeFor(unittest.TestCase):
    """Python code snippet generation."""

    def test_code_contains_model_id(self):
        code = gmx.python_code_for("mistral-large-4-1t-a52b")
        self.assertIn('"model": "mistral-large-4-1t-a52b"', code)
        self.assertIn("invoke_url = \"https://integrate.api.nvidia.com/v1/chat/completions\"", code)
        self.assertIn("import requests", code)

    def test_code_contains_gemini_model(self):
        code = gmx.python_code_for("gemini-flash-lite")
        self.assertIn('"model": "gemini-flash-lite"', code)

    def test_code_contains_stream_false(self):
        code = gmx.python_code_for("some-model")
        self.assertIn("stream = False", code)


class TestBuildXml(unittest.TestCase):
    """XML building from parsed model entries."""

    def test_build_xml_structure(self):
        models = [
            {
                "alias": "mistral-large-4-1t-a52b",
                "full_alias": "mistralai/mistral-large-4-1t-a52b",
                "name": "Mistral Large 4 Model by Mistral AI",
                "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
            }
        ]
        xml = gmx.build_xml(models)

        self.assertIn('<?xml version="1.0" encoding="utf-8"?>', xml)
        self.assertIn('<models>', xml)
        self.assertIn('</models>', xml)
        self.assertIn('<model id="mistral-large-4-1t-a52b">', xml)
        self.assertIn("<name>mistral-large-4-1t-a52b</name>", xml)
        self.assertIn(
            "<full-model-name>Mistral Large 4 Model by Mistral AI</full-model-name>", xml
        )
        self.assertIn(
            "<url>https://integrate.api.nvidia.com/v1/chat/completions</url>", xml
        )
        self.assertIn("<python-code><![CDATA[", xml)
        self.assertIn("]]></python-code>", xml)

    def test_build_xml_multiple_models(self):
        models = [
            {
                "alias": "model-a",
                "full_alias": "org/model-a",
                "name": "Model A",
                "endpoint": "https://endpoint.a/v1/chat/completions",
            },
            {
                "alias": "model-b",
                "full_alias": "org/model-b",
                "name": "Model B",
                "endpoint": "https://endpoint.b/v1/chat/completions",
            },
        ]
        xml = gmx.build_xml(models)
        self.assertEqual(xml.count("<model id="), 2)
        self.assertEqual(xml.count("</model>"), 2)

    def test_build_xml_empty(self):
        xml = gmx.build_xml([])
        self.assertIn('<models>', xml)
        self.assertIn('</models>', xml)
        self.assertNotIn('<model ', xml)


if __name__ == "__main__":
    unittest.main()
