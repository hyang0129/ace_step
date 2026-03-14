"""Tests for ace_step.client — AceStepClient against a mock HTTP backend."""

from __future__ import annotations

import json

import httpx
import pytest

from ace_step.client import (
    AceStepClient,
    AceStepError,
    AceStepTimeout,
    TaskResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_response(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        content=json.dumps(data).encode(),
        headers={"content-type": "application/json"},
    )


def _audio_response(audio: bytes = b"\x00" * 100) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        content=audio,
        headers={"content-type": "audio/mpeg"},
    )


def _succeeded_query_result(task_id: str, audio_path: str = "/v1/audio?path=test.mp3"):
    """Build a query_result response matching the upstream ACE-Step format."""
    result_list = [{"file": audio_path, "status": 1, "stage": "succeeded"}]
    return {
        "data": [
            {
                "task_id": task_id,
                "result": json.dumps(result_list),
                "status": 1,
            }
        ],
        "code": 200,
    }


def _failed_query_result(task_id: str, error: str = "OOM"):
    result_list = [{"file": "", "status": 2, "error": error, "stage": "failed"}]
    return {
        "data": [
            {
                "task_id": task_id,
                "result": json.dumps(result_list),
                "status": 2,
            }
        ],
        "code": 200,
    }


def _running_query_result(task_id: str):
    result_list = [{"file": "", "status": 0, "stage": "running", "progress": 0.5}]
    return {
        "data": [
            {
                "task_id": task_id,
                "result": json.dumps(result_list),
                "status": 0,
            }
        ],
        "code": 200,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealth:
    @pytest.mark.asyncio
    async def test_healthy(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"status": "ok"})
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert await client.health() is True
        await client.close()

    @pytest.mark.asyncio
    async def test_unhealthy(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="error")
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert await client.health() is False
        await client.close()


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success(self):
        """Happy path: submit -> poll (succeeded) -> download audio."""

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-123"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    _succeeded_query_result("t-123", "/v1/audio?path=out.mp3")
                )
            elif "/v1/audio" in url:
                return _audio_response(b"FAKEAUDIO")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        result = await client.generate(
            description="gentle piano", duration=30
        )
        assert isinstance(result, TaskResult)
        assert result.task_id == "t-123"
        assert result.audio_bytes == b"FAKEAUDIO"
        assert result.duration_s == 30.0
        await client.close()

    @pytest.mark.asyncio
    async def test_release_task_error(self):
        transport = httpx.MockTransport(
            lambda req: _json_response(
                {"code": 500, "error": "model not loaded"}, status=200
            )
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        with pytest.raises(AceStepError, match="model not loaded"):
            await client.generate(description="test")
        await client.close()

    @pytest.mark.asyncio
    async def test_task_failed(self):
        """Backend reports the task failed."""

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-fail"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    _failed_query_result("t-fail", "OOM")
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        with pytest.raises(AceStepError, match="failed"):
            await client.generate(description="test")
        await client.close()

    @pytest.mark.asyncio
    async def test_optional_params_forwarded(self):
        """Ensure bpm, key, time_signature make it into the payload."""
        captured_body = {}

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                captured_body.update(json.loads(request.content))
                return _json_response(
                    {"data": {"task_id": "t-opt"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    _succeeded_query_result("t-opt")
                )
            elif "/v1/audio" in url:
                return _audio_response()
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        await client.generate(
            description="test",
            bpm=120,
            key="Am",
            time_signature=3,
        )
        # Flat payload format matching GenerateMusicRequest
        assert captured_body["bpm"] == 120
        assert captured_body["key_scale"] == "Am"
        assert captured_body["time_signature"] == "3"
        assert captured_body["prompt"] == "test"
        assert captured_body["task_type"] == "text2music"
        await client.close()

    @pytest.mark.asyncio
    async def test_polls_until_complete(self):
        """Client retries when data is empty (task still processing)."""
        poll_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-poll"}, "code": 200}
                )
            elif "/query_result" in url:
                poll_count += 1
                if poll_count < 3:
                    # Empty data = still processing
                    return _json_response({"data": [], "code": 200})
                return _json_response(
                    _succeeded_query_result("t-poll")
                )
            elif "/v1/audio" in url:
                return _audio_response(b"DONE")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        result = await client.generate(description="test")
        assert result.audio_bytes == b"DONE"
        assert poll_count == 3
        await client.close()

    @pytest.mark.asyncio
    async def test_running_status_keeps_polling(self):
        """Status 0 (running) keeps polling until succeeded."""
        poll_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-run"}, "code": 200}
                )
            elif "/query_result" in url:
                poll_count += 1
                if poll_count < 2:
                    return _json_response(_running_query_result("t-run"))
                return _json_response(
                    _succeeded_query_result("t-run")
                )
            elif "/v1/audio" in url:
                return _audio_response(b"READY")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        result = await client.generate(description="test")
        assert result.audio_bytes == b"READY"
        assert poll_count == 2
        await client.close()


class TestTaskResult:
    def test_save_to_file(self, tmp_path):
        result = TaskResult(
            task_id="t-1",
            audio_bytes=b"hello",
            duration_s=10.0,
            sample_rate=48000,
            format="mp3",
        )
        dest = tmp_path / "sub" / "output.mp3"
        returned = result.save_to_file(dest)
        assert returned == dest
        assert dest.read_bytes() == b"hello"


class TestSyncWrappers:
    def test_health_sync_true(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"status": "ok"})
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert client.health_sync() is True

    def test_health_sync_false(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(500, text="error")
        )
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        assert client.health_sync() is False

    def test_generate_sync_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-sync"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    _succeeded_query_result("t-sync")
                )
            elif "/v1/audio" in url:
                return _audio_response(b"SYNCAUDIO")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        result = client.generate_sync(description="sync test", duration=15)
        assert result.audio_bytes == b"SYNCAUDIO"
        assert result.task_id == "t-sync"

    def test_generate_sync_called_twice(self):
        """Calling generate_sync twice should not fail with event loop errors."""

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "/release_task" in url:
                return _json_response(
                    {"data": {"task_id": "t-twice"}, "code": 200}
                )
            elif "/query_result" in url:
                return _json_response(
                    _succeeded_query_result("t-twice")
                )
            elif "/v1/audio" in url:
                return _audio_response(b"AUDIO")
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        client = AceStepClient.__new__(AceStepClient)
        client._base_url = "http://test"
        client._http = httpx.AsyncClient(transport=transport, base_url="http://test")

        r1 = client.generate_sync(description="first")
        r2 = client.generate_sync(description="second")
        assert r1.audio_bytes == b"AUDIO"
        assert r2.audio_bytes == b"AUDIO"
