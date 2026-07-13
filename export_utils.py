"""Export utilities for search results."""

import os
import csv
import io
import json
from typing import List
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

from providers.base import CompanyInfo


def export_to_csv(data: List[CompanyInfo], filepath: str) -> str:
    """Export company data to CSV file. Returns the file path."""
    fieldnames = [
        "company_name", "credit_code", "legal_person", "reg_capital",
        "reg_date", "address", "phone", "mobile_phone", "landline_phone",
        "email", "status", "industry", "province", "city"
    ]
    headers_cn = {
        "company_name": "企业名称",
        "credit_code": "统一社会信用代码",
        "legal_person": "法定代表人",
        "reg_capital": "注册资本",
        "reg_date": "成立日期",
        "address": "地址",
        "phone": "联系电话",
        "mobile_phone": "手机号",
        "landline_phone": "座机",
        "email": "邮箱",
        "status": "经营状态",
        "industry": "行业",
        "province": "省份",
        "city": "城市",
    }

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(headers_cn)
        for item in data:
            row = {}
            for k in fieldnames:
                v = getattr(item, k, "")
                row[k] = "; ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else (v or "")
            writer.writerow(row)

    return filepath


def export_to_excel(data: List[CompanyInfo], filepath: str) -> str:
    """Export company data to Excel file. Returns the file path."""
    wb = Workbook()
    ws = wb.active
    ws.title = "企业数据"

    # Headers
    headers_cn = [
        "企业名称", "统一社会信用代码", "法定代表人", "注册资本",
        "成立日期", "地址", "手机号", "座机", "联系电话",
        "区县",
        "邮箱", "经营状态", "行业", "省份", "城市"
    ]
    fieldnames = [
        "company_name", "credit_code", "legal_person", "reg_capital",
        "reg_date", "address", "phone", "mobile_phone", "landline_phone",
        "email", "status", "industry", "province", "city"
    ]

    # Style header row
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    for col_idx, header in enumerate(headers_cn, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Data rows
    for row_idx, item in enumerate(data, 2):
        for col_idx, field in enumerate(fieldnames, 1):
            raw = getattr(item, field, "")
            # 安全转换: openpyxl 不支持 list/tuple/None
            if isinstance(raw, (list, tuple)):
                val = "; ".join(str(v) for v in raw)
            elif raw is None:
                val = ""
            else:
                val = raw
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.alignment = Alignment(vertical="center")
            cell.border = thin_border

    # Auto-adjust column widths
    for col_idx, header in enumerate(headers_cn, 1):
        max_len = len(header)
        for row_idx in range(2, min(len(data) + 2, 100)):
            cell_val = ws.cell(row=row_idx, column=col_idx).value
            if cell_val:
                max_len = max(max_len, len(str(cell_val)))
        ws.column_dimensions[chr(64 + col_idx)].width = min(max_len + 4, 40)

    wb.save(filepath)
    return filepath


def export_json(data: List[CompanyInfo], filepath: str) -> str:
    """Export company data to JSON file."""
    fieldnames = [
        "company_name", "credit_code", "legal_person", "reg_capital",
        "reg_date", "address", "phone", "mobile_phone", "landline_phone",
        "email", "status", "industry", "province", "city"
    ]
    rows = [{k: getattr(item, k, "") for k in fieldnames} for item in data]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    return filepath
