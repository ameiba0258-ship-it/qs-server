"""百度地图 POI 搜索 provider implementation.

高德数据偏本地生活服务（餐饮、购物等），
百度地图的数据结构类似但企业登记的电话号码覆盖不太一样，
两者互补使用可获得更多联系方式。

API 文档: https://lbsyun.baidu.com/index.php?title=webapi/guide/webservice-placeapi
免费额度: ~4000次/天（个人开发者）
"""

import re
from typing import List, Optional
import httpx

from .base import DataProvider, CompanyInfo, SearchParams, SearchResult


def _parse_phones_baidu(raw_phone: str):
    """Parse Baidu phone field into (mobile, landline)."""
    if not raw_phone:
        return "", ""
    parts = re.split(r'[,;，；、/\s]+', str(raw_phone))
    mobiles, landlines = [], []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        cleaned = p.replace('-', '').replace(' ', '')
        if re.match(r'^1[3-9]\d{9}$', cleaned):
            mobiles.append(p)
        elif re.match(r'^0\d{2,3}-?\d{7,8}$', cleaned) or re.match(r'^\d{7,8}$', cleaned):
            landlines.append(p)
        elif re.match(r'^[48]00\d{7,8}$', cleaned):
            landlines.append(p)
        elif re.match(r'^[\d\- ]{7,15}$', p):
            landlines.append(p)
    return "; ".join(mobiles), "; ".join(landlines)


class BaiduMapProvider(DataProvider):
    """Provider for 百度地图 POI search.

    注册: https://lbsyun.baidu.com → 控制台 → 应用管理 → 创建应用
    选择「服务端」类型，获取 API Key
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.map.baidu.com/place/v2"

    async def search(self, params: SearchParams) -> SearchResult:
        if not self.api_key:
            raise ValueError("百度地图 API Key 未配置")

        # Build query params
        query_params = {
            "query": params.keyword,
            "region": params.city or params.province or "全国",
            "output": "json",
            "ak": self.api_key,
            "page_size": min(params.page_size or 20, 20),
            "page_num": params.page - 1,  # Baidu uses 0-based pages
            "scope": "2",  # 2 = detailed info (includes telephone)
        }

        try:
            url = f"{self.base_url}/search"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=query_params)
                data = resp.json()
        except Exception as e:
            return SearchResult(total=0, data=[])

        if data.get("status") != 0:
            err_msg = data.get("message", "未知错误")
            if err_msg != "ok":
                raise ValueError(f"百度地图 API 错误: {err_msg}")
            return SearchResult(total=0, data=[])

        results = data.get("results", [])
        total = int(data.get("total", 0))

        pois = []
        for item in results:
            phone_raw = item.get("telephone", "")
            mobile, landline = _parse_phones_baidu(phone_raw)
            addr = item.get("address", "")
            # Baidu returns province/city in separate fields
            prov = item.get("province", "")
            city = item.get("city", "")
            area = item.get("area", "")

            company = CompanyInfo(
                id=item.get("uid", ""),
                company_name=item.get("name", ""),
                address=addr,
                phone=phone_raw,
                mobile_phone=mobile,
                landline_phone=landline,
                industry=item.get("detail", ""),
                province=prov,
                city=city,
                district=area,
            )
            pois.append(company)

        return SearchResult(total=total, data=pois)

    async def batch_search(
        self, params: SearchParams, max_results: int = 3000,
        progress_callback=None
    ) -> List[CompanyInfo]:
        """Override: Baidu max 400 results (20 pages × 20 items)."""
        all_data: List[CompanyInfo] = []
        page = 1
        max_pages = min(20, max_results // 20 + 1)

        while page <= max_pages and len(all_data) < max_results:
            params.page = page
            result = await self.search(params)
            if not result.data:
                break
            all_data.extend(result.data)
            if progress_callback:
                progress_callback(len(all_data), min(result.total, max_results))
            page += 1

        return all_data[:max_results]

    def get_contact_info(self, company_id: str) -> dict:
        return {"phone": "", "email": ""}
