"""腾讯地图 POI 搜索 provider implementation。

月免费额度: 1,000,000 次（个人开发者）
注册: https://lbs.qq.com → 控制台 → 应用管理 → 创建应用 → 获取 Key
"""

import re
from typing import List, Optional
import httpx

from .base import DataProvider, CompanyInfo, SearchParams, SearchResult


def _parse_phones(raw: str):
    if not raw:
        return "", ""
    parts = re.split(r'[,;，；、/\s]+', str(raw))
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


class TencentMapProvider(DataProvider):
    """Provider for 腾讯地图 POI search."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://apis.map.qq.com/ws/place/v1"

    async def search(self, params: SearchParams) -> SearchResult:
        if not self.api_key:
            raise ValueError("腾讯地图 API Key 未配置")

        region = params.city or params.province or "全国"
        query_params = {
            "keyword": params.keyword,
            "boundary": f"region({region},1)",
            "page_size": min(params.page_size or 20, 20),
            "page_index": params.page,
            "key": self.api_key,
            "output": "json",
        }

        try:
            url = f"{self.base_url}/search"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=query_params)
                data = resp.json()
        except Exception as e:
            return SearchResult(total=0, data=[])

        if data.get("status") != 0:
            return SearchResult(total=0, data=[])

        pois = data.get("data", [])
        total = int(data.get("count", 0))

        results = []
        for item in pois:
            ad_info = item.get("ad_info", {})
            phone_raw = item.get("tel", "")
            mobile, landline = _parse_phones(phone_raw)

            company = CompanyInfo(
                id=item.get("id", ""),
                company_name=item.get("title", ""),
                address=item.get("address", ""),
                phone=phone_raw,
                mobile_phone=mobile,
                landline_phone=landline,
                industry=item.get("category", ""),
                province=ad_info.get("province", ""),
                city=ad_info.get("city", ""),
                district=ad_info.get("district", ""),
            )
            results.append(company)

        return SearchResult(total=total, data=results)

    async def batch_search(
        self, params: SearchParams, max_results: int = 3000,
        progress_callback=None
    ) -> List[CompanyInfo]:
        all_data: List[CompanyInfo] = []
        page = 1
        max_pages = min(10, max_results // 20 + 1)
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
