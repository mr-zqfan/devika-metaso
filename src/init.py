import os
from src.config import Config
from src.logger import Logger


def init_devika():
    logger = Logger()

    logger.info("Initializing Devika...")
    logger.info("checking configurations...")

    config = Config()

    http_proxy = config.get_proxy_http_proxy()
    if http_proxy:
        logger.info(f"Using http_proxy: {http_proxy}")
        os.environ["http_proxy"] = http_proxy
    https_proxy = config.get_proxy_https_proxy()
    if https_proxy:
        logger.info(f"Using https_proxy: {https_proxy}")
        os.environ["https_proxy"] = https_proxy
    no_proxy = config.get_proxy_no_proxy()
    if no_proxy:
        logger.info(f"Using no_proxy: {no_proxy}")
        os.environ["no_proxy"] = no_proxy

    sqlite_db = config.get_sqlite_db()
    screenshots_dir = config.get_screenshots_dir()
    pdfs_dir = config.get_pdfs_dir()
    projects_dir = config.get_projects_dir()
    logs_dir = config.get_logs_dir()

    logger.info("Initializing Prerequisites Jobs...")
    os.makedirs(os.path.dirname(sqlite_db), exist_ok=True)
    os.makedirs(screenshots_dir, exist_ok=True)
    os.makedirs(pdfs_dir, exist_ok=True)
    os.makedirs(projects_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    if config.get_features_enable_keyword_extraction():
        from src.bert.sentence import SentenceBert

        logger.info("Loading sentence-transformer BERT models...")
        prompt = "Light-weight keyword extraction exercise for BERT model loading.".strip()
        SentenceBert(prompt).extract_keywords()
        logger.info("BERT model loaded successfully.")
