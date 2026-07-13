"""Abstract base class for data providers."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CompanyInfo:
    id: str = ""
    company_name: str = ""
    credit_code: str = ""
    legal_person: str = ""
    reg_capital: str = ""
    reg_date: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    status: str = ""
    industry: str = ""
    province: str = ""
    city: str = ""
    district: str = ""
    mobile_phone: str = ""
    landline_phone: str = ""


@dataclass
class SearchParams:
    provider: str = "amap"
    keyword: str = ""
    province: str = ""
    city: str = ""
    district: str = ""
    industry: str = ""
    reg_capital_min: Optional[float] = None
    reg_capital_max: Optional[float] = None
    reg_date_start: str = ""
    reg_date_end: str = ""
    page: int = 1
    page_size: int = 20
    keywords: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    total: int = 0
    data: List[CompanyInfo] = field(default_factory=list)


class DataProvider:
    """Base data provider. Override methods for each API."""

    async def search(self, params: SearchParams) -> SearchResult:
        raise NotImplementedError

    async def batch_search(
        self, params: SearchParams, max_results: int = 3000,
        progress_callback=None
    ) -> List[CompanyInfo]:
        """Fetch multiple pages up to max_results."""
        all_data: List[CompanyInfo] = []
        page = 1

        while len(all_data) < max_results:
            params.page = page
            result = await self.search(params)
            if not result.data:
                break
            all_data.extend(result.data)
            if progress_callback:
                progress_callback(len(all_data), min(result.total, max_results))
            if len(all_data) >= result.total or len(all_data) >= max_results:
                break
            page += 1

        return all_data[:max_results]

    def get_contact_info(self, company_id: str) -> dict:
        raise NotImplementedError
