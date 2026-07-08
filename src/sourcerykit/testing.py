"""Testing utilities for SourceryKit examples and tests.

Provides a lightweight mock HTTP server for running examples without
external dependencies (e.g., httpbin.org).

Usage::

    from sourcerykit.testing import start_mock_server

    async def main():
        runner, url = await start_mock_server()
        try:
            # use url in your HTTP calls
            await insert_trusted_endpoint(url=url)
        finally:
            await runner.cleanup()
"""

from aiohttp import web


async def _echo_handler(request: web.Request) -> web.Response:
    """Echo back the POST body under a 'json' key (matches httpbin.org/post format)."""
    data = await request.json()
    return web.json_response({"json": data})


async def start_mock_server() -> tuple[web.AppRunner, str]:
    """Start a local echo server on a random port.

    The server echoes back any POST body under a ``json`` key, matching the
    format of ``httpbin.org/post``.

    Returns:
        A ``(runner, url)`` tuple. Call ``await runner.cleanup()`` when done.
    """
    app = web.Application()
    app.router.add_post("/post", _echo_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 0)
    await site.start()
    assert site._server is not None
    port = site._server.sockets[0].getsockname()[1]  # type: ignore[attr-defined]
    return runner, f"http://localhost:{port}/post"
