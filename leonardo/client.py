"""Core API client for Leonardo AI."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .exceptions import (
    LeonardoAPIError,
    LeonardoAuthError,
    LeonardoGenerationError,
    LeonardoRateLimitError,
    LeonardoTimeoutError,
)
from .models import (
    Generation,
    GenerationRequest,
    GenerationStatus,
    PlatformModel,
    UserInfo,
)

logger = logging.getLogger(__name__)


class LeonardoClient:
    """Client for interacting with Leonardo AI REST API."""

    DEFAULT_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_POLL_INTERVAL = 5.0
    DEFAULT_POLL_TIMEOUT = 300.0

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Leonardo API client.

        Args:
            api_key: Leonardo API key
            base_url: API base URL (defaults to cloud.leonardo.ai)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "LeonardoClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise appropriate exceptions."""
        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text}

        if response.status_code == 401:
            raise LeonardoAuthError(
                "Invalid API key or unauthorized access",
                status_code=401,
                response=data,
            )
        elif response.status_code == 403:
            raise LeonardoAuthError(
                "Access forbidden - check API key permissions",
                status_code=403,
                response=data,
            )
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise LeonardoRateLimitError(
                "Rate limit exceeded",
                status_code=429,
                retry_after=int(retry_after) if retry_after else None,
                response=data,
            )
        elif response.status_code >= 400:
            error_msg = data.get("error", data.get("message", str(data)))
            raise LeonardoAPIError(
                f"API error: {error_msg}",
                status_code=response.status_code,
                response=data,
            )

        return data

    @retry(
        retry=retry_if_exception_type(LeonardoRateLimitError),
        wait=wait_exponential_jitter(initial=1, max=60, jitter=5),
        stop=stop_after_attempt(5),
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict:
        """Make an API request with retry logic."""
        logger.debug(f"{method} {endpoint}")
        response = self.client.request(method, endpoint, **kwargs)
        return self._handle_response(response)

    def verify_api_key(self) -> UserInfo:
        """
        Verify API key and get user info.

        Returns:
            UserInfo with account details

        Raises:
            LeonardoAuthError: If API key is invalid
        """
        data = self._request("GET", "/me")
        user_data = data.get("user_details", [{}])
        if isinstance(user_data, list) and user_data:
            user_data = user_data[0]

        # API returns nested structure with user info under "user" key
        nested_user = user_data.get("user", {})
        flat_data = {
            "id": nested_user.get("id", ""),
            "username": nested_user.get("username"),
            "tokenRenewalDate": user_data.get("tokenRenewalDate"),
            "subscriptionTokens": user_data.get("subscriptionTokens"),
            "apiCredit": user_data.get("apiSubscriptionTokens"),
        }
        return UserInfo(**flat_data)

    def list_models(self) -> list[PlatformModel]:
        """
        List available platform models.

        Returns:
            List of available models
        """
        data = self._request("GET", "/platformModels")
        models_data = data.get("custom_models", [])
        return [PlatformModel(**m) for m in models_data]

    def create_generation(
        self,
        prompt: str,
        model_id: str | None = None,
        width: int = 2550,
        height: int = 3300,
        seed: int | None = None,
        negative_prompt: str | None = None,
        num_images: int = 1,
        **kwargs,
    ) -> str:
        """
        Create a new image generation request.

        Args:
            prompt: Generation prompt
            model_id: Model ID to use
            width: Image width in pixels
            height: Image height in pixels
            seed: Random seed for reproducibility
            negative_prompt: Negative prompt
            num_images: Number of images to generate
            **kwargs: Additional generation parameters

        Returns:
            Generation ID

        Raises:
            LeonardoAPIError: If generation request fails
        """
        request = GenerationRequest(
            prompt=prompt,
            modelId=model_id,
            width=width,
            height=height,
            seed=seed,
            negative_prompt=negative_prompt,
            num_images=num_images,
            **kwargs,
        )

        # Build request body, excluding None values
        body = {k: v for k, v in request.model_dump().items() if v is not None}

        logger.info(f"Creating generation: {prompt[:50]}...")
        data = self._request("POST", "/generations", json=body)

        generation_data = data.get("sdGenerationJob", {})
        gen_id = generation_data.get("generationId")

        if not gen_id:
            raise LeonardoAPIError(
                "No generation ID returned",
                response=data,
            )

        logger.info(f"Generation created: {gen_id}")
        return gen_id

    def get_generation(self, generation_id: str) -> Generation:
        """
        Get generation status and results.

        Args:
            generation_id: ID of the generation to fetch

        Returns:
            Generation with status and images
        """
        data = self._request("GET", f"/generations/{generation_id}")
        gen_data = data.get("generations_by_pk", {})
        return Generation(**gen_data)

    def poll_until_complete(
        self,
        generation_id: str,
        timeout: float | None = None,
        interval: float | None = None,
    ) -> Generation:
        """
        Poll generation until complete or timeout.

        Args:
            generation_id: ID of the generation to poll
            timeout: Maximum time to wait in seconds
            interval: Polling interval in seconds

        Returns:
            Completed generation

        Raises:
            LeonardoTimeoutError: If polling times out
            LeonardoGenerationError: If generation fails
        """
        timeout = timeout or self.DEFAULT_POLL_TIMEOUT
        interval = interval or self.DEFAULT_POLL_INTERVAL
        start_time = time.time()

        logger.info(f"Polling generation {generation_id}...")

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise LeonardoTimeoutError(
                    f"Generation {generation_id} timed out after {timeout}s"
                )

            generation = self.get_generation(generation_id)

            if generation.status == GenerationStatus.COMPLETE:
                logger.info(
                    f"Generation {generation_id} complete with "
                    f"{len(generation.generated_images)} images"
                )
                return generation

            if generation.status == GenerationStatus.FAILED:
                raise LeonardoGenerationError(
                    f"Generation {generation_id} failed",
                    generation_id=generation_id,
                )

            logger.debug(
                f"Generation {generation_id} status: {generation.status}, "
                f"elapsed: {elapsed:.1f}s"
            )
            time.sleep(interval)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, LeonardoRateLimitError)),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=3),
        stop=stop_after_attempt(5),
    )
    def download_image(
        self,
        url: str,
        dest_path: Path | str,
        overwrite: bool = False,
    ) -> Path:
        """
        Download an image from URL to local path.

        Args:
            url: Image URL
            dest_path: Destination file path
            overwrite: Whether to overwrite existing files

        Returns:
            Path to downloaded file
        """
        dest_path = Path(dest_path)

        if dest_path.exists() and not overwrite:
            logger.debug(f"File already exists: {dest_path}")
            return dest_path

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading image to {dest_path}")

        # Use a separate client for downloads (no auth needed)
        with httpx.Client(timeout=self.timeout) as download_client:
            response = download_client.get(url)
            response.raise_for_status()

            with open(dest_path, "wb") as f:
                f.write(response.content)

        logger.debug(f"Downloaded {len(response.content)} bytes to {dest_path}")
        return dest_path

    def generate_and_download(
        self,
        prompt: str,
        output_dir: Path | str,
        filename_prefix: str = "page",
        poll_timeout: float | None = None,
        **generation_kwargs,
    ) -> list[Path]:
        """
        Create generation, poll until complete, and download all images.

        Args:
            prompt: Generation prompt
            output_dir: Directory to save images
            filename_prefix: Prefix for downloaded filenames
            poll_timeout: Polling timeout
            **generation_kwargs: Additional args for create_generation

        Returns:
            List of paths to downloaded images
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        gen_id = self.create_generation(prompt, **generation_kwargs)
        generation = self.poll_until_complete(gen_id, timeout=poll_timeout)

        downloaded = []
        for i, img in enumerate(generation.generated_images):
            ext = "png"  # Leonardo typically returns PNG
            filename = f"{filename_prefix}_{gen_id}_{i}.{ext}"
            dest = output_dir / filename
            self.download_image(img.url, dest)
            downloaded.append(dest)

        return downloaded
