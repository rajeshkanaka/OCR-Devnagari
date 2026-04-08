"""Tests for the ChandraBackend OCR backend."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from ocr_hindi.backends.chandra_backend import ChandraBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def backend():
    """Return a fresh ChandraBackend instance (not initialised)."""
    return ChandraBackend()


@pytest.fixture
def tiny_image():
    """1x1 white PIL image for tests that don't need real content."""
    return Image.new("RGB", (1, 1), "white")


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_name(self, backend):
        assert backend.name == "chandra"

    def test_is_free(self, backend):
        assert backend.is_free is True

    def test_cost_per_1000_pages(self, backend):
        assert backend.cost_per_1000_pages == 0.0


# ---------------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------------


class TestInitialize:
    def test_missing_dependency_returns_false(self, backend):
        with patch.dict("sys.modules", {"chandra": None, "chandra.model": None}):
            ok, msg = backend.initialize()
        assert ok is False
        assert "not installed" in msg.lower()

    def test_successful_init(self, backend):
        mock_manager = MagicMock()
        mock_module = MagicMock()
        mock_module.InferenceManager.return_value = mock_manager

        with patch.dict("sys.modules", {"chandra": MagicMock(), "chandra.model": mock_module}):
            ok, msg = backend.initialize()

        assert ok is True
        assert "ready" in msg.lower()
        assert backend._initialized is True
        assert backend._manager is mock_manager

    def test_init_exception_returns_false(self, backend):
        mock_module = MagicMock()
        mock_module.InferenceManager.side_effect = RuntimeError("boom")

        with patch.dict("sys.modules", {"chandra": MagicMock(), "chandra.model": mock_module}):
            ok, msg = backend.initialize()

        assert ok is False
        assert "boom" in msg


# ---------------------------------------------------------------------------
# process_image()
# ---------------------------------------------------------------------------


class TestProcessImage:
    def test_not_initialized_returns_failure(self, backend, tiny_image):
        result = backend.process_image(tiny_image, page_num=1)
        assert result.success is False
        assert "not initialized" in result.error.lower()

    def test_empty_results_returns_failure(self, backend, tiny_image):
        backend._initialized = True
        backend._manager = MagicMock()
        backend._manager.generate.return_value = []

        mock_schema = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "chandra": MagicMock(),
                "chandra.model": MagicMock(),
                "chandra.model.schema": mock_schema,
            },
        ):
            result = backend.process_image(tiny_image, page_num=1)

        assert result.success is False
        assert "no results" in result.error.lower()

    def test_successful_processing(self, backend, tiny_image):
        backend._initialized = True
        backend._manager = MagicMock()

        fake_result = SimpleNamespace(markdown="## Title\n\nHello world")
        backend._manager.generate.return_value = [fake_result]

        mock_schema = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "chandra": MagicMock(),
                "chandra.model": MagicMock(),
                "chandra.model.schema": mock_schema,
            },
        ):
            result = backend.process_image(tiny_image, page_num=3)

        assert result.success is True
        assert result.page_num == 3
        assert "Hello world" in result.text
        assert result.backend_used == "chandra"
        assert result.confidence > 0

    def test_preserve_markdown_flag(self, backend, tiny_image):
        backend.preserve_markdown = True
        backend._initialized = True
        backend._manager = MagicMock()

        fake_result = SimpleNamespace(markdown="## Title\n\n**bold text**")
        backend._manager.generate.return_value = [fake_result]

        mock_schema = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "chandra": MagicMock(),
                "chandra.model": MagicMock(),
                "chandra.model.schema": mock_schema,
            },
        ):
            result = backend.process_image(tiny_image, page_num=1)

        assert "##" in result.text
        assert "**" in result.text

    def test_missing_markdown_attr_returns_empty(self, backend, tiny_image):
        backend._initialized = True
        backend._manager = MagicMock()

        fake_result = SimpleNamespace()  # no .markdown attribute
        backend._manager.generate.return_value = [fake_result]

        mock_schema = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "chandra": MagicMock(),
                "chandra.model": MagicMock(),
                "chandra.model.schema": mock_schema,
            },
        ):
            result = backend.process_image(tiny_image, page_num=1)

        assert result.success is True
        assert result.text == ""

    def test_exception_during_processing(self, backend, tiny_image):
        backend._initialized = True
        backend._manager = MagicMock()
        backend._manager.generate.side_effect = RuntimeError("GPU OOM")

        mock_schema = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "chandra": MagicMock(),
                "chandra.model": MagicMock(),
                "chandra.model.schema": mock_schema,
            },
        ):
            result = backend.process_image(tiny_image, page_num=2)

        assert result.success is False
        assert "GPU OOM" in result.error


# ---------------------------------------------------------------------------
# _strip_markdown()
# ---------------------------------------------------------------------------


class TestStripMarkdown:
    def test_removes_headings(self):
        assert ChandraBackend._strip_markdown("## Hello") == "Hello"

    def test_removes_bold(self):
        assert ChandraBackend._strip_markdown("**bold**") == "bold"

    def test_removes_italic(self):
        assert ChandraBackend._strip_markdown("*italic*") == "italic"

    def test_removes_hr(self):
        assert ChandraBackend._strip_markdown("---") == ""

    def test_removes_links(self):
        assert ChandraBackend._strip_markdown("[text](http://x.com)") == "text"

    def test_collapses_blank_lines(self):
        result = ChandraBackend._strip_markdown("a\n\n\n\nb")
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# _estimate_confidence()
# ---------------------------------------------------------------------------


class TestEstimateConfidence:
    def test_empty_text(self):
        assert ChandraBackend._estimate_confidence("") == 0.0

    def test_good_text(self):
        text = "This is a good paragraph of text with enough length to be confident."
        conf = ChandraBackend._estimate_confidence(text)
        assert conf >= 0.85

    def test_short_text(self):
        conf = ChandraBackend._estimate_confidence("hi")
        assert conf < 1.0

    def test_garbage_text(self):
        conf = ChandraBackend._estimate_confidence("!@#$%^&*()" * 3)
        assert conf < 0.85

    def test_floor_at_0_4(self):
        conf = ChandraBackend._estimate_confidence("12345")
        assert conf >= 0.4


# ---------------------------------------------------------------------------
# cleanup()
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_resets_state(self, backend):
        backend._manager = MagicMock()
        backend._initialized = True

        backend.cleanup()

        assert backend._manager is None
        assert backend._initialized is False

    def test_cleanup_when_already_clean(self, backend):
        backend.cleanup()  # should not raise
        assert backend._manager is None

    @patch("ocr_hindi.backends.chandra_backend.torch", create=True)
    def test_cleanup_calls_cuda_empty_cache(self, mock_torch, backend):
        backend._manager = MagicMock()
        backend._initialized = True
        mock_torch.cuda.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            backend.cleanup()

        mock_torch.cuda.empty_cache.assert_called_once()
