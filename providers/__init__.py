from .base import DataProvider, CompanyInfo, SearchParams
from .amap import AmapProvider
from .baidumap import BaiduMapProvider
from .tencentmap import TencentMapProvider


def get_provider(name: str = "amap", api_key: str = "") -> DataProvider:
    if name == "amap":
        return AmapProvider(api_key)
    if name == "baidumap":
        return BaiduMapProvider(api_key)
    if name == "tencentmap":
        return TencentMapProvider(api_key)
    raise ValueError(f"Unknown provider: {name}")


__all__ = ["DataProvider", "CompanyInfo", "SearchParams", "AmapProvider", "BaiduMapProvider", "TencentMapProvider", "get_provider"]
