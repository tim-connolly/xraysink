"""Test the background task helpers."""

from typing import Optional
from urllib.parse import urlparse

import pytest
from aws_xray_sdk.core.models.segment import Segment

from xraysink.tasks import xray_task_async

pytestmark = pytest.mark.asyncio


class TestXrayTaskAsync:
    """Test the xray_task_async() decorator."""

    async def _verify_http_segment(
        self, segment: Segment, expected_path: Optional[str] = None
    ):
        request_data = segment.http["request"]

        assert (
            request_data["client_ip"] == "127.0.0.1"
        ), "Should use localhost as client IP for synthetic HTTP request."

        assert request_data["user_agent"].startswith("BackgroundTask")
        assert "xraysink" in request_data["user_agent"]

        url = urlparse(request_data["url"])
        assert url.scheme == "task", "Should use synthetic URL scheme"
        assert (
            url.netloc == "localhost"
        ), "Should use localhost for hostname in synthetic URL"
        if expected_path is not None:
            assert url.path == expected_path, "URL should use synthetic path"

        assert (
            "method" not in request_data
        ), "Should not use HTTP method in synthetic request - that's *too* confusing."
        assert (
            "x_forwarded_for" not in request_data
        ), "Should not provide any indication about HTTP headers in synthetic request."

        assert (
            "response" not in segment.http
        ), "Should not provide any HTTP response data for synthetic request."

    async def test_should_create_segment_with_synthetic_http_request(self, recorder):
        # Setup SUT function
        @xray_task_async()
        async def do_something(a, b):
            return a + b

        # Exercise
        func_result = await do_something(1, 2)

        # Verify
        assert func_result == 3, "Function result should be returned"

        segment = recorder.emitter.pop()
        assert not segment.in_progress
        assert not getattr(segment, "error", False)
        assert not getattr(segment, "fault", False)

        await self._verify_http_segment(segment, expected_path="/do_something")