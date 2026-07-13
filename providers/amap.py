"""高德地图 POI 搜索 provider implementation."""

import json
import re
from typing import List, Optional
import httpx

def _parse_phones(raw_phone: str):
    """Parse phone into (mobile, landline)."""
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

from .base import DataProvider, CompanyInfo, SearchParams, SearchResult


class AmapApiError(Exception):
    """高德 API 返回的业务错误。"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class AmapProvider(DataProvider):
    """Provider for 高德地图 POI search.
    
    高德开放平台: https://lbs.amap.com/api/webservice/guide/api/search
    个人开发者免费额度: 5000次/天
    """

    POI_TYPES = {
        "": "全部类型",
        "170000": "公司企业",
        "050000": "餐饮服务",
        "060000": "购物服务",
        "070000": "生活服务",
        "100000": "住宿服务",
        "090000": "医疗保健服务",
        "140000": "科教文化服务",
        "160000": "金融保险服务",
        "080000": "体育休闲服务",
        "010000": "汽车服务",
        "020000": "汽车销售",
        "030000": "汽车维修",
        "130000": "政府机构及社会团体",
        "120000": "商务住宅",
        "110000": "风景名胜",
        "150000": "交通设施服务",
    }

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3/place"

    async def search(self, params: SearchParams) -> SearchResult:
        """Search POIs via 高德地图文本搜索API。"""
        if not self.api_key:
            raise AmapApiError("NO_API_KEY", "高德 API Key 未配置")

        query_params = {
            "key": self.api_key,
            "keywords": params.keyword,
            "offset": min(params.page_size or 20, 25),
            "page": params.page,
            "extensions": "all",
        }

        # City filter
        if params.city:
            query_params["city"] = params.city
        elif params.province:
            p = params.province.replace("省", "").replace("市", "").replace("壮族", "")\
                               .replace("回族", "").replace("维吾尔", "").replace("自治区", "")
            query_params["city"] = p[:2]

        if params.industry:
            query_params["types"] = params.industry

        try:
            url = f"{self.base_url}/text"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=query_params)
                data = resp.json()
        except httpx.TimeoutException:
            raise AmapApiError("TIMEOUT", "高德 API 请求超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            raise AmapApiError("HTTP_ERROR", f"高德 API HTTP 错误: {e.response.status_code}")
        except Exception as e:
            raise AmapApiError("NETWORK_ERROR", f"网络请求失败: {str(e)}")

        # 高德 API 返回 status=0 表示业务错误
        if data.get("status") != "1":
            info = data.get("info", "未知错误")
            infocode = data.get("infocode", "")
            errmsg = f"高德 API 错误: {info}"
            if infocode:
                errmsg += f" (代码: {infocode})"

            if info == "USER_DAILY_QUERY_OVER_LIMIT":
                errmsg += " — 今日免费调用次数已用完，明天再试或升级"
            elif info == "INVALID_USER_KEY":
                errmsg += " — API Key 无效，请检查配置"
            elif info == "SERVICE_NOT_AVAILABLE":
                errmsg += " — 该服务暂不可用"
            elif info == "DAILY_QUERY_OVER_LIMIT":
                errmsg += " — 每日调用量超限"
            elif info == "ACCESS_TOO_FREQUENT":
                errmsg += " — 访问太频繁，请稍后再试"

            raise AmapApiError(infocode or info, errmsg)

        pois = data.get("pois", [])
        total = int(data.get("count", 0))

        results = []
        for poi in pois:
            phone_raw = poi.get("tel", "")
            mobile, landline = _parse_phones(phone_raw)
            company = CompanyInfo(
                id=poi.get("id", ""),
                company_name=poi.get("name", ""),
                credit_code="",
                legal_person="",
                reg_capital="",
                reg_date="",
                address=poi.get("address", ""),
                phone=phone_raw,
                mobile_phone=mobile,
                landline_phone=landline,
                email="",
                status="",
                industry=poi.get("type", ""),
                province=poi.get("pname", ""),
                city=poi.get("cityname", ""),
                district=poi.get("adname", ""),
            )
            results.append(company)

        return SearchResult(total=total, data=results)

    async def batch_search(
        self, params: SearchParams, max_results: int = 3000,
        progress_callback=None
    ) -> List[CompanyInfo]:
        """Override batch search for 高德（API 上限 100 条）。"""
        all_data: List[CompanyInfo] = []
        page = 1
        max_pages = min(4, max_results // 25 + 1)

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
