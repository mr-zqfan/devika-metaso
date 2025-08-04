
import requests

import logging

from src.config import Config

LOGGER = logging.getLogger(__name__)


class Metaso:
    def __init__(self):
        config = Config()
        self.api_key = config.get_metaso_api_key()
        self.base_url = config.get_metaso_api_base_url()

    def inference(self, model_id: str, prompt: str) -> str:
        LOGGER.debug(f"no use proxy for metaso search")
        res = requests.post(self.base_url,
                            headers={
                                "Authorization": f"Bearer {self.api_key}",
                                "Accept": "application/json",
                                "Content-Type": "application/json"
                            },
                            json={
                                "q": prompt.strip(),
                                "model": model_id,
                                "format": "simple",
                                "conciseSnippet": True,
                            },
                            timeout=180)

        return res.json().get("answer", "").strip() if res.status_code == 200 else f"Error: {res.status_code} - {res.text}"
