from __future__ import annotations

import logging
import re
import urllib.parse

import aiohttp
import orjson

BASE_URL = "https://portaal.eplucon.nl"
_LOGGER: logging.Logger = logging.getLogger(__package__)


class ApiAuthError(Exception):
    pass


class ApiError(Exception):
    pass


class EpluconWeb:
    """Client to talk to Eplucon API"""

    def __init__(
        self,
        web_username: str,
        web_password: str,
        web_endpoint: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._base = web_endpoint if web_endpoint else BASE_URL
        self._session = session or aiohttp.ClientSession()
        self._headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        }

        self._username = web_username
        self._password = web_password

        _LOGGER.debug("Initialize Eplucon Web client")

    async def close(self) -> None:
        await self._session.close()

    async def _get_login_page(self, url: str) -> tuple[dict[str, str], str]:
        _LOGGER.debug("Cookies and login page saved.")

        # Send a GET request to fetch the login page
        cookies = {}
        html_content = ""
        async with self._session.get(url) as response:
            for cookie in self._session.cookie_jar:
                cookies[cookie.key] = cookie.value

            html_content = await response.text()

        return cookies, html_content

    def _get_csrf_token(self, html_content: str) -> str | None:
        # Extract the CSRF token using a regex
        csrf_token_match = re.search(
            r'<meta name="csrf-token" content="([^"]+)"', html_content
        )

        # Get the token if the regex matches
        csrf_token = csrf_token_match.group(1) if csrf_token_match else None
        return csrf_token

    def _get_token(self, html_content: str) -> str | None:
        # Extract the token using a regex
        token_match = re.search(
            r'<input type="hidden" name="_token" value="([^"]+)"', html_content
        )

        # Get the token if the regex matches
        token = token_match.group(1) if token_match else None
        return token

    def _get_valid_from(self, html_content: str) -> str | None:
        # Extract the valid_from value using a regex
        valid_from_match = re.search(
            r'<input name="valid_from"[^>]*value="([^"]*)"', html_content, re.DOTALL
        )

        # Get the valid_from value if the regex matches
        valid_from = valid_from_match.group(1) if valid_from_match else None
        return valid_from

    def _get_my_name(self, html_content: str) -> str | None:
        # Extract the my_name value using a regex
        my_name_match = re.search(r'<input id="my_name[^"]*"', html_content)

        # Get the my_name value if the regex matches
        my_name = (
            my_name_match.group(0).split('id="')[1].split('"')[0]
            if my_name_match
            else None
        )
        return my_name

    async def login(self) -> tuple[None, None] | tuple[str, str]:
        url = f"{self._base}/login"
        _LOGGER.debug(f"Eplucon Web login {url}")

        cookies, login_page = await self._get_login_page(url)

        remember = 1

        enc_username = urllib.parse.quote(self._username)
        enc_password = urllib.parse.quote(self._password)
        csrf_token = self._get_csrf_token(html_content=login_page)
        enc_csrf_token = urllib.parse.quote(csrf_token or "")
        valid_from = self._get_valid_from(html_content=login_page)
        enc_valid_from = urllib.parse.quote(valid_from or "")
        my_name = self._get_my_name(html_content=login_page)
        enc_my_name = urllib.parse.quote(my_name or "")

        # encode url form data
        data = (
            f"{enc_my_name}=&"
            f"valid_from={enc_valid_from}&"
            f"_token={enc_csrf_token}&"
            f"username={enc_username}&"
            f"password={enc_password}&"
            f"remember={remember}"
        )

        self._headers["Origin"] = self._base
        self._headers["Referer"] = url

        for key, value in cookies.items():
            self._session.cookie_jar.update_cookies({key: value})

        web_cookie = (None, None)
        async with self._session.post(
            url, headers=self._headers, data=data
        ) as response:
            response.raise_for_status()

            for cookie in self._session.cookie_jar:
                if cookie.key.startswith("remember_web"):
                    web_cookie = cookie.key, cookie.value
                    return web_cookie

        return web_cookie

    async def get_ajax(self, web_cookie: tuple[str, str], node_id: int) -> str | None:
        url = f"{self._base}/e-control/ajax/tile/info/{node_id}"

        cookies = {web_cookie[0]: web_cookie[1]}

        async with self._session.get(url, cookies=cookies) as response:
            response.raise_for_status()
            response_str = await response.text()
            if response_str:
                json_response = orjson.loads(response_str)
                return orjson.dumps(json_response, option=orjson.OPT_INDENT_2).decode()

            else:
                return None
