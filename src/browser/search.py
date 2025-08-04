
import logging
import re
from urllib.parse import unquote
from html import unescape
import orjson
import requests
import grequests

from src.config import Config

LOGGER = logging.getLogger(__name__)


def is_no_sites_url(url):
    """Check if the URL is in the no_sites list."""
    for site in Config().get_web_search_no_sites():
        if site in url:
            LOGGER.debug(f"URL {url} is in no_sites list: {site}")
            return True
    return False


class MetasoSearch:
    """本引擎直接给出结果"""
    def __init__(self):
        config = Config()
        self.api_key = config.get_metaso_api_key()
        self.base_url = config.get_metaso_api_base_url()

    def search(self, query):
        LOGGER.debug(f"no use proxy for metaso search")
        return grequests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json={
                "q": query.strip(),
                "model": "fast",
                "format": "simple",
                "conciseSnippet": True,
            },
            timeout=180)

    def get_first_link(self):
        raise NotImplementedError("MetasoSearch does not support get_first_link method. Use inference method instead.")


class BingSearch:
    def __init__(self):
        self.config = Config()
        self.bing_api_key = self.config.get_bing_api_key()
        self.bing_api_endpoint = self.config.get_bing_api_endpoint()
        self.query_result = None

    def search(self, query):
        headers = {"Ocp-Apim-Subscription-Key": self.bing_api_key}
        params = {"q": query, "mkt": "en-US"}

        try:
            response = requests.get(self.bing_api_endpoint, headers=headers, params=params)
            response.raise_for_status()
            self.query_result = response.json()
            return self.query_result
        except Exception as error:
            return error

    def get_first_link(self):
        item = ''
        if self.query_result is None or "webPages" not in self.query_result or "value" not in self.query_result["webPages"]:
            LOGGER.error("No web pages found in Bing search result.")
            return item

        for i in range(len(self.query_result["webPages"]["value"])):
            item = self.query_result["webPages"]["value"][i]["url"]
            if not is_no_sites_url(item):
                return item
        return item


class GoogleSearch:
    def __init__(self):
        self.config = Config()
        self.google_search_api_key = self.config.get_google_search_api_key()
        self.google_search_engine_ID = self.config.get_google_search_engine_id()
        self.google_search_api_endpoint = self.config.get_google_search_api_endpoint()
        self.query_result = None

    def search(self, query):
        params = {
            "key": self.google_search_api_key,
            "cx": self.google_search_engine_ID,
            "q": query
        }
        try:
            print("Searching in Google...")
            response = requests.get(self.google_search_api_endpoint, params=params)
            # response.raise_for_status()
            self.query_result = response.json()
        except Exception as error:
            return error

    def get_first_link(self):
        item = ""
        try:
            # if 'items' in self.query_result:
            #     item = self.query_result['items'][0]['link']
            # return item
            if 'items' in self.query_result:
                for i in range(len(self.query_result['items'])):
                    item = self.query_result['items'][i]['link']
                    if not is_no_sites_url(item):
                        return item

            return item
        except Exception as error:
            print(error)
            return ""

# class DuckDuckGoSearch:
#     def __init__(self):
#         self.query_result = None
#
#     def search(self, query):
#         from duckduckgo_search import DDGS
#         try:
#             self.query_result = DDGS().text(query, max_results=5, region="us")
#             print(self.query_result)
#
#         except Exception as err:
#             print(err)
#
#     def get_first_link(self):
#         if self.query_result:
#             return self.query_result[0]["href"]
#         else:
#             return None
#


class DuckDuckGoSearch:
    """DuckDuckGo search engine class.
    methods are inherited from the duckduckgo_search package.
    do not change the methods.

    currently, the package is not working with our current setup.
    """
    def __init__(self):
        from curl_cffi import requests as curl_requests
        self.query_result = None
        self.asession = curl_requests.Session(impersonate="chrome", allow_redirects=False)
        self.asession.headers["Referer"] = "https://duckduckgo.com/"

    def _get_url(self, method, url, data):
        try:
            resp = self.asession.request(method, url, data=data)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == (202, 301, 403):
                raise Exception(f"Error: {resp.status_code} rate limit error")
            if not resp:
                return None
        except Exception as error:
            if "timeout" in str(error).lower():
                raise TimeoutError("Duckduckgo timed out error")

    def duck(self, query):
        resp = self._get_url("POST", "https://duckduckgo.com/", data={"q": query})
        vqd = self.extract_vqd(resp)

        params = {"q": query, "kl": 'en-us', "p": "1", "s": "0", "df": "", "vqd": vqd, "ex": ""}
        resp = self._get_url("GET", "https://links.duckduckgo.com/d.js", params)
        page_data = self.text_extract_json(resp)

        results = []
        for row in page_data:
            href = row.get("u")
            if href and href != f"http://www.google.com/search?q={query}":
                body = self.normalize(row["a"])
                if body:
                    result = {
                        "title": self.normalize(row["t"]),
                        "href": self.normalize_url(href),
                        "body": self.normalize(row["a"]),
                    }
                    results.append(result)

        self.query_result = results

    def search(self, query):
        self.duck(query)

    def get_first_link(self):
        item = ''
        for i in range(len(self.query_result)):
            item = self.query_result[i]['href']
            if not is_no_sites_url(item):
                return item
        return item

    @staticmethod
    def extract_vqd(html_bytes: bytes) -> str:
        patterns = [(b'vqd="', 5, b'"'), (b"vqd=", 4, b"&"), (b"vqd='", 5, b"'")]
        for start_pattern, offset, end_pattern in patterns:
            try:
                start = html_bytes.index(start_pattern) + offset
                end = html_bytes.index(end_pattern, start)
                return html_bytes[start:end].decode()
            except ValueError:
                continue

    @staticmethod
    def text_extract_json(html_bytes):
        try:
            start = html_bytes.index(b"DDG.pageLayout.load('d',") + 24
            end = html_bytes.index(b");DDG.duckbar.load(", start)
            return orjson.loads(html_bytes[start:end])
        except Exception as ex:
            print(f"Error extracting JSON: {type(ex).__name__}: {ex}")

    @staticmethod
    def normalize_url(url: str) -> str:
        return unquote(url.replace(" ", "+")) if url else ""

    @staticmethod
    def normalize(raw_html: str) -> str:
        return unescape(re.sub("<.*?>", "", raw_html)) if raw_html else ""
