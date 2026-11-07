#!/usr/bin/env python3
"""Functional tests for tools/robota.py.

Tests HTML parsing functions using fake HTML content. No network calls are made.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SUT = Path(__file__).resolve().parents[1] / "robota.py"  # tools/robota.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("robota_sut", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rb = _load_sut()


class TestExtractModelLinks(unittest.TestCase):
    """Extract model detail links from listing page HTML."""

    def test_extract_model_links(self):
        html = """
        <html>
        <body>
        <a href="/models/mistralai/mistral-large-4-1t-a52b">Mistral Large 4</a>
        <a href="/models/nvidia/nemotron-3.5-bolt-e4b">Nemotron Bolt</a>
        <a href="/models/explore/discover">Explore</a>
        <a href="/models/models/community">Community</a>
        </body>
        </html>
        """
        links = rb.extract_model_links(html)
        self.assertEqual(len(links), 2)
        self.assertIn(("mistralai/mistral-large-4-1t-a52b", "https://build.nvidia.com/models/mistralai/mistral-large-4-1t-a52b"), links)
        self.assertIn(("nvidia/nemotron-3.5-bolt-e4b", "https://build.nvidia.com/models/nvidia/nemotron-3.5-bolt-e4b"), links)

    def test_extract_relative_links(self):
        html = '<a href="/models/mistralai/mistral-large-4-1t-a52b">Mistral</a>'
        links = rb.extract_model_links(html)
        self.assertEqual(len(links), 1)

    def test_no_links(self):
        html = "<html><body>No links here</body></html>"
        self.assertEqual(rb.extract_model_links(html), [])


class TestIsUnavailable(unittest.TestCase):
    """Unavailable pattern detection."""

    def test_unavailable_notice(self):
        html = "API access for this model is not available yet."
        self.assertTrue(rb.is_unavailable(html))

    def test_not_open_for_programmatic_access(self):
        html = "This endpoint is not open for programmatic access."
        self.assertTrue(rb.is_unavailable(html))

    def test_no_api_key_will_authorize(self):
        html = "no API key will authorize it."
        self.assertTrue(rb.is_unavailable(html))

    def test_available(self):
        html = "This model has a free endpoint."
        self.assertFalse(rb.is_unavailable(html))


class TestHasFreeEndpoint(unittest.TestCase):
    """Free endpoint detection."""

    def test_has_free_endpoint(self):
        html = "This model has a free endpoint."
        self.assertTrue(rb.has_free_endpoint(html))

    def test_has_free_api(self):
        html = "Free API access available."
        self.assertTrue(rb.has_free_endpoint(html))

    def test_no_free_endpoint(self):
        html = "Paid model only."
        self.assertFalse(rb.has_free_endpoint(html))


class TestExtractTitle(unittest.TestCase):
    """Page title extraction."""

    def test_extract_title_from_title_tag(self):
        html = '<title>Mistral Large 4 Model by Mistral AI | NVIDIA NIM</title>'
        self.assertEqual(rb.extract_title(html), "Mistral Large 4 Model by Mistral AI | NVIDIA NIM")

    def test_extract_title_from_h1(self):
        html = "<h1>Nemotron 3.5 Bolt E4B Model by NVIDIA</h1>"
        self.assertEqual(rb.extract_title(html), "Nemotron 3.5 Bolt E4B Model by NVIDIA")

    def test_no_title(self):
        self.assertEqual(rb.extract_title("<html><body></body></html>", ), "")


class TestExtractEndpoint(unittest.TestCase):
    """Endpoint URL extraction."""

    def test_extract_endpoint(self):
        html = 'https://integrate.api.nvidia.com/v1/chat/completions'
        self.assertEqual(
            rb.extract_endpoint(html),
            "https://integrate.api.nvidia.com/v1/chat/completions",
        )

    def test_no_endpoint(self):
        self.assertIsNone(rb.extract_endpoint("No endpoint here"))


class TestLooksLikeLlm(unittest.TestCase):
    """LLM detection heuristic."""

    def test_is_llm(self):
        html = "This is a large language model for chat/completions."
        self.assertTrue(rb.looks_like_llm(html))

    def test_is_not_llm(self):
        html = "This is an image generation model."
        self.assertFalse(rb.looks_like_llm(html))


if __name__ == "__main__":
    unittest.main()
