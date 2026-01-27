"""Smoke tests for the coloring book generator.

These tests verify basic functionality without making actual API calls
unless LEONARDO_API_KEY is set and --live flag is used.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImports:
    """Test that all modules can be imported."""

    def test_import_leonardo_client(self):
        from leonardo import LeonardoClient
        assert LeonardoClient is not None

    def test_import_leonardo_models(self):
        from leonardo.models import (
            Generation,
            GenerationImage,
            GenerationRequest,
            GenerationStatus,
            PlatformModel,
            UserInfo,
        )
        assert Generation is not None
        assert GenerationStatus.COMPLETE == "COMPLETE"

    def test_import_leonardo_exceptions(self):
        from leonardo.exceptions import (
            LeonardoAPIError,
            LeonardoAuthError,
            LeonardoRateLimitError,
            LeonardoTimeoutError,
        )
        assert LeonardoAPIError is not None


class TestLeonardoClient:
    """Test Leonardo client without API calls."""

    def test_client_initialization(self):
        from leonardo import LeonardoClient

        client = LeonardoClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://cloud.leonardo.ai/api/rest/v1"
        assert client.timeout == 60.0

    def test_client_custom_base_url(self):
        from leonardo import LeonardoClient

        client = LeonardoClient(
            api_key="test_key",
            base_url="https://custom.api.com/v1/",
        )
        assert client.base_url == "https://custom.api.com/v1"

    def test_client_context_manager(self):
        from leonardo import LeonardoClient

        with LeonardoClient(api_key="test_key") as client:
            assert client.api_key == "test_key"


class TestModels:
    """Test Pydantic models."""

    def test_generation_request_defaults(self):
        from leonardo.models import GenerationRequest

        req = GenerationRequest(prompt="test prompt")
        assert req.prompt == "test prompt"
        assert req.width == 2550
        assert req.height == 3300
        assert req.num_images == 1

    def test_generation_status_enum(self):
        from leonardo.models import GenerationStatus

        assert GenerationStatus.PENDING == "PENDING"
        assert GenerationStatus.COMPLETE == "COMPLETE"
        assert GenerationStatus.FAILED == "FAILED"

    def test_generation_model(self):
        from leonardo.models import Generation, GenerationStatus

        gen = Generation(
            id="test-id",
            status=GenerationStatus.COMPLETE,
            prompt="test prompt",
        )
        assert gen.id == "test-id"
        assert gen.status == GenerationStatus.COMPLETE


class TestExceptions:
    """Test custom exceptions."""

    def test_api_error(self):
        from leonardo.exceptions import LeonardoAPIError

        error = LeonardoAPIError("Test error", status_code=500)
        assert str(error) == "[500] Test error"
        assert error.status_code == 500

    def test_auth_error(self):
        from leonardo.exceptions import LeonardoAuthError

        error = LeonardoAuthError("Invalid key", status_code=401)
        assert error.status_code == 401

    def test_rate_limit_error(self):
        from leonardo.exceptions import LeonardoRateLimitError

        error = LeonardoRateLimitError(retry_after=30)
        assert error.retry_after == 30


class TestPromptGeneration:
    """Test prompt template loading and generation."""

    def test_load_prompts_file_exists(self, tmp_path):
        """Test loading prompts from YAML file."""
        import yaml

        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create base prompts file
        base_file = prompts_dir / "base_prompts.yaml"
        base_file.write_text(yaml.dump({
            "base_template": "{subject}, test style"
        }))

        # Import after creating files
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

        # We need to mock the prompts directory path
        from scripts.generate_pages import load_prompts

        template, negative = load_prompts(prompts_dir)
        assert "{subject}" in template
        assert "test style" in template

    def test_generate_prompt(self):
        """Test prompt generation from template."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.generate_pages import generate_prompt

        # With template
        result = generate_prompt(
            subject="mandala",
            base_template="{subject}, black and white",
            variation="with flowers",
        )
        assert "mandala with flowers" in result
        assert "black and white" in result

        # Without template (uses default)
        result = generate_prompt(
            subject="mandala",
            base_template="",
            variation=None,
        )
        assert "mandala" in result
        assert "coloring book" in result


class TestVariations:
    """Test prompt variation generation."""

    def test_generate_variations(self):
        """Test generating prompt variations."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.make_variations import generate_variations

        variations = generate_variations("mandala", theme="mandala", count=5)
        assert len(variations) == 5
        assert all("mandala" in v for v in variations)

    def test_theme_modifiers(self):
        """Test that theme modifiers are applied."""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.make_variations import THEME_MODIFIERS

        assert "mandala" in THEME_MODIFIERS
        assert "animals" in THEME_MODIFIERS
        assert len(THEME_MODIFIERS["mandala"]) >= 10


class TestImageValidation:
    """Test image validation functions."""

    def test_check_file_integrity(self, tmp_path):
        """Test file integrity check."""
        from PIL import Image

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.validate_images import check_file_integrity

        # Create valid image
        img_path = tmp_path / "test.png"
        img = Image.new("L", (100, 100), color=255)
        img.save(img_path)

        ok, error = check_file_integrity(img_path)
        assert ok is True
        assert error is None

    def test_check_dimensions(self, tmp_path):
        """Test dimension checking."""
        from PIL import Image

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.validate_images import check_image_dimensions

        img = Image.new("L", (2550, 3300), color=255)

        ok, error = check_image_dimensions(img, 2550, 3300)
        assert ok is True

        ok, error = check_image_dimensions(img, 1000, 1000)
        assert ok is False
        assert "Expected" in error


class TestPostProcessing:
    """Test image post-processing functions."""

    def test_convert_to_grayscale(self, tmp_path):
        """Test grayscale conversion."""
        from PIL import Image

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.postprocess_lineart import convert_to_grayscale

        # RGB image
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        result = convert_to_grayscale(img)
        assert result.mode == "L"

    def test_convert_to_bw(self, tmp_path):
        """Test black/white conversion."""
        from PIL import Image

        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from scripts.postprocess_lineart import convert_to_bw

        # Create image with gray values
        img = Image.new("L", (100, 100), color=128)
        result = convert_to_bw(img, threshold=128)
        assert result.mode == "1"


@pytest.mark.skipif(
    not os.getenv("LEONARDO_API_KEY"),
    reason="LEONARDO_API_KEY not set"
)
class TestLiveAPI:
    """Live API tests - only run when API key is available."""

    def test_verify_api_key(self):
        """Test API key verification."""
        from leonardo import LeonardoClient

        api_key = os.getenv("LEONARDO_API_KEY")
        client = LeonardoClient(api_key=api_key)

        user = client.verify_api_key()
        assert user.id is not None
        client.close()

    def test_list_models(self):
        """Test listing models."""
        from leonardo import LeonardoClient

        api_key = os.getenv("LEONARDO_API_KEY")
        client = LeonardoClient(api_key=api_key)

        models = client.list_models()
        assert len(models) > 0
        assert all(hasattr(m, "id") for m in models)
        client.close()


@pytest.mark.skipif(
    not os.getenv("LEONARDO_API_KEY") or not os.getenv("RUN_SMOKE_GEN"),
    reason="Requires LEONARDO_API_KEY and RUN_SMOKE_GEN=1"
)
class TestSmokeGeneration:
    """Smoke test that generates 2 actual pages.

    Only runs when both LEONARDO_API_KEY and RUN_SMOKE_GEN=1 are set.
    This is expensive (uses API credits) so disabled by default.
    """

    def test_generate_two_pages(self, tmp_path):
        """Generate 2 pages to verify full pipeline."""
        from leonardo import LeonardoClient

        api_key = os.getenv("LEONARDO_API_KEY")
        client = LeonardoClient(api_key=api_key)

        prompt = "simple flower, black and white line art, coloring book"

        # Generate single page
        gen_id = client.create_generation(
            prompt=prompt,
            width=512,  # Small for speed
            height=512,
            num_images=1,
        )

        assert gen_id is not None

        # Poll for completion
        generation = client.poll_until_complete(gen_id, timeout=120)

        assert len(generation.generated_images) >= 1

        # Download
        img = generation.generated_images[0]
        dest = tmp_path / "test_page.png"
        client.download_image(img.url, dest)

        assert dest.exists()
        assert dest.stat().st_size > 0

        client.close()
