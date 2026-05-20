"""真样本集成测试。

样本位于 docs/sample/（已 .gitignore，本机才能跑）。
找不到样本时 skip，不算失败。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.sdk import parse_invoice

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "docs" / "sample"


def _load(name: str) -> bytes | None:
    p = SAMPLE_DIR / name
    return p.read_bytes() if p.is_file() else None


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "普票1.pdf",
            {
                "invoice_number": "26317000001791661472",
                "issue_date": "2026-05-17",
                "buyer_name": "浙江捷发科技股份有限公司",
                "seller_name": "上海捞派餐饮管理有限公司",
                "amount_without_tax": "199.06",
                "tax_amount": "11.94",
                "amount_with_tax": "211.00",
                "amount_in_words": "贰佰壹拾壹圆整",
            },
        ),
        (
            "普票2.pdf",
            {
                "invoice_number": "25337000000316455014",
                "issue_date": "2025-08-18",
                "buyer_name": "浙江捷发科技股份有限公司",
                "seller_name": "中国电信股份有限公司绍兴分公司",
                "amount_without_tax": "139.50",
                "tax_amount": None,
                "amount_with_tax": "139.50",
                "amount_in_words": "壹佰叁拾玖圆伍角",
            },
        ),
    ],
)
def test_digital_general_real_sample(filename: str, expected: dict) -> None:
    content = _load(filename)
    if content is None:
        pytest.skip(f"样本缺失: {filename}（属正常，docs/sample 不入库）")

    data = parse_invoice(content)
    assert data["invoice_type"] == "digital_general"
    assert data["invoice_number"] == expected["invoice_number"]
    assert data["issue_date"] == expected["issue_date"]
    assert data["buyer"]["name"] == expected["buyer_name"]
    assert data["seller"]["name"] == expected["seller_name"]
    assert data["amount_without_tax"] == expected["amount_without_tax"]
    assert data["tax_amount"] == expected["tax_amount"]
    assert data["amount_with_tax"] == expected["amount_with_tax"]
    assert data["amount_in_words"] == expected["amount_in_words"]
    # 双方税号必须捕获
    assert data["buyer"]["tax_id"], "buyer tax_id 缺失"
    assert data["seller"]["tax_id"], "seller tax_id 缺失"
    # source 必须填齐
    assert data["source"]["format"] == "pdf"
    assert data["source"]["extracted_by"] == "text_layer"
