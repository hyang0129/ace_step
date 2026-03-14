"""Async client for the ACE-Step v1.5 built-in API server.

ACE-Step exposes a task-based REST API (default http://localhost:8001).
This client wraps the submit -> poll -> download flow behind a single
async method so callers get a simple generate-and-get-bytes interface.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ACESTEP_BASE_URL = os.environ.get("ACESTEP_BASE_URL", "http://localhost:8001")
POLL_INTERVAL_S = float(os.environ.get("ACESTEP_POLL_INTERVAL", "1.0"))
POLL_TIMEOUT_S = float(os.environ.get("ACESTEP_POLL_TIMEOUT", "300"))

# ACE-Step query_result status codes
_STATUS_RUNNING = 0
_STATUS_SUCCEEDED = 1
_STATUS_FAILED = 2


class AceStepError(Exception):
    """Raised when the ACE-Step backend returns an error."""


class AceStepTimeout(AceStepError):
    """Raised when polling for a task result exceeds the timeout."""


@dataclass(slots=True)
class TaskResult:
    """Resolved result from ACE-Step."""

    task_id: str
    audio_bytes: bytes
    duration_s: float
    sample_rate: int
    format: str

    def save_to_file(self, path: str | os.PathLike[str]) -> Path:
        """Write audio bytes to *path* and return the resolved Path."""
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.audio_bytes)
        return dest


class AceStepClient:
    """Thin async wrapper around ACE-Step's REST API.

    Lifecycle: create once during app lifespan, close on shutdown.
    """

    def __init__(self, base_url: str = ACESTEP_BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    # -- health -----------------------------------------------------------

    async def health(self) -> bool:
        """Return *True* if the ACE-Step server is reachable."""
        try:
            resp = await self._http.get("/health")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # -- generation -------------------------------------------------------

    async def generate(
        self,
        *,
        description: str,
        duration: int = 30,
        instrumental: bool = True,
        bpm: int | None = None,
        key: str | None = None,
        time_signature: int | None = None,
        guidance_scale: float = 7.0,
        num_inference_steps: int = 8,
        seed: int = -1,
        audio_format: str = "wav",
    ) -> TaskResult:
        """Submit a generation task, poll until complete, return audio bytes."""

        # Build flat payload matching GenerateMusicRequest schema
        payload: dict[str, Any] = {
            "prompt": description,
            "audio_duration": duration,
            "inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "audio_format": audio_format,
            "task_type": "text2music",
        }
        if instrumental:
            payload["lyrics"] = ""
        if bpm is not None:
            payload["bpm"] = bpm
        if key is not None:
            payload["key_scale"] = key
        if time_signature is not None:
            payload["time_signature"] = str(time_signature)

        # Submit
        resp = await self._http.post("/release_task", json=payload)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") != 200:
            raise AceStepError(f"release_task failed: {body.get('error')}")
        task_id: str = body["data"]["task_id"]
        logger.info("Submitted task %s", task_id)

        # Poll for completion
        audio_url = await self._poll_task(task_id)

        # Download audio
        audio_bytes = await self._download_audio(audio_url)

        return TaskResult(
            task_id=task_id,
            audio_bytes=audio_bytes,
            duration_s=float(duration),
            sample_rate=48000,
            format=audio_format,
        )

    # -- internals --------------------------------------------------------

    async def _poll_task(self, task_id: str) -> str:
        """Poll /query_result until task completes, return audio download URL."""
        elapsed = 0.0
        while elapsed < POLL_TIMEOUT_S:
            resp = await self._http.post(
                "/query_result",
                json={"task_id_list": [task_id]},
            )
            resp.raise_for_status()
            body = resp.json()
            if body.get("code") != 200:
                raise AceStepError(f"query_result error: {body.get('error')}")

            data = body.get("data", [])
            if not data:
                await asyncio.sleep(POLL_INTERVAL_S)
                elapsed += POLL_INTERVAL_S
                continue

            item = data[0]
            status = item.get("status", _STATUS_RUNNING)

            if status == _STATUS_SUCCEEDED:
                # result is a JSON string containing array of file entries
                result_str = item.get("result", "[]")
                try:
                    result_list = json.loads(result_str)
                except (json.JSONDecodeError, TypeError):
                    result_list = []
                if not result_list:
                    raise AceStepError(f"Task {task_id} succeeded but no audio files")
                # Return the first file's download URL
                return result_list[0].get("file", "")

            if status == _STATUS_FAILED:
                result_str = item.get("result", "[]")
                try:
                    result_list = json.loads(result_str)
                    error = result_list[0].get("error", "unknown") if result_list else "unknown"
                except (json.JSONDecodeError, TypeError):
                    error = "unknown"
                raise AceStepError(f"Task {task_id} failed: {error}")

            await asyncio.sleep(POLL_INTERVAL_S)
            elapsed += POLL_INTERVAL_S

        raise AceStepTimeout(
            f"Task {task_id} did not complete within {POLL_TIMEOUT_S}s"
        )

    async def _download_audio(self, audio_url: str) -> bytes:
        """Download generated audio from the server-provided URL path."""
        resp = await self._http.get(audio_url)
        resp.raise_for_status()
        return resp.content

    # -- sync wrappers ----------------------------------------------------

    def _make_sync_client(self) -> httpx.AsyncClient:
        """Create a fresh AsyncClient matching the original config.

        Preserves any mock transport set on the original client (for tests).
        """
        transport = getattr(self._http, "_transport", None)
        kwargs: dict[str, Any] = {
            "base_url": self._base_url,
            "timeout": 30.0,
        }
        if transport is not None and not isinstance(transport, httpx.AsyncHTTPTransport):
            kwargs["transport"] = transport
        return httpx.AsyncClient(**kwargs)

    def generate_sync(self, **kwargs: Any) -> TaskResult:
        """Blocking wrapper around :meth:`generate` for sync callers.

        Creates a fresh event loop + async client each call to avoid
        'Event loop is closed' errors when called multiple times.
        """
        async def _run() -> TaskResult:
            async with self._make_sync_client() as http:
                old = self._http
                self._http = http
                try:
                    return await self.generate(**kwargs)
                finally:
                    self._http = old

        return asyncio.run(_run())

    def health_sync(self) -> bool:
        """Blocking wrapper around :meth:`health`.

        Creates a fresh event loop + async client each call.
        """
        async def _run() -> bool:
            async with self._make_sync_client() as http:
                old = self._http
                self._http = http
                try:
                    return await self.health()
                finally:
                    self._http = old

        return asyncio.run(_run())

    # -- lifecycle --------------------------------------------------------

    async def close(self) -> None:
        await self._http.aclose()
