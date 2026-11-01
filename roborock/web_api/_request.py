"""Low-level HTTP request helper shared by every web API module."""

import logging

import aiohttp
from aiohttp import ContentTypeError

from roborock.exceptions import RoborockException

_LOGGER = logging.getLogger(__name__)


class PreparedRequest:
    def __init__(
        self, base_url: str, session: aiohttp.ClientSession | None = None, base_headers: dict | None = None
    ) -> None:
        self.base_url = base_url
        self.base_headers = base_headers or {}
        self.session = session

    async def request(self, method: str, url: str, params=None, data=None, headers=None, json=None) -> dict:
        _url = "/".join(s.strip("/") for s in [self.base_url, url])
        _headers = {**self.base_headers, **(headers or {})}
        close_session = self.session is None
        session = self.session if self.session is not None else aiohttp.ClientSession()
        try:
            async with session.request(method, _url, params=params, data=data, headers=_headers, json=json) as resp:
                return await resp.json()
        except ContentTypeError as err:
            """If we get an error, lets log everything for debugging."""
            try:
                resp_json = await resp.json(content_type=None)
                _LOGGER.info("Resp: %s", resp_json)
            except ContentTypeError as err_2:
                _LOGGER.info(err_2)
            resp_raw = await resp.read()
            _LOGGER.info("Resp raw: %s", resp_raw)
            # Still raise the err so that it's clear it failed.
            raise err
        except (aiohttp.ClientError, TimeoutError, OSError) as err:
            raise RoborockException(f"Network error contacting {_url}: {err}") from err
        finally:
            if close_session:
                await session.close()
