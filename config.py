"""Configuration management."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # 高德地图
    AMAP_API_KEY: str = os.getenv("AMAP_API_KEY", "")
    # 百度地图
    BAIDU_API_KEY: str = os.getenv("BAIDU_API_KEY", "")
    TENCENT_API_KEY: str = os.getenv("TENCENT_API_KEY", "")
    # 服务
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "9876"))
    PAGE_SIZE: int = 20
    MAX_RESULTS: int = 100
    EXPORT_DIR: str = os.path.join(os.path.dirname(__file__), "exports")


settings = Settings()


def get_amap_api_key() -> str:
    """读取高德 API Key（每次实时读 os.environ，支持运行时更新）。"""
    return os.environ.get("AMAP_API_KEY", "")


def get_baidu_api_key() -> str:
    """读取百度地图 API Key。"""
    return os.environ.get("BAIDU_API_KEY", "")


def get_tencent_api_key() -> str:
    return os.environ.get("TENCENT_API_KEY", "")
