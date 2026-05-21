"""真样本集成测试。

样本位于 docs/sample/（已 .gitignore，本机才能跑）。
找不到样本时 skip，不算失败。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.sdk import parse_invoice

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "docs" / "sample"
MANIFEST = SAMPLE_DIR / "manifest.json"


def _load(name: str) -> bytes | None:
    p = SAMPLE_DIR / name
    return p.read_bytes() if p.is_file() else None


def _manifest_cases() -> list[dict]:
    if not MANIFEST.is_file():
        return []
    import json

    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return payload.get("files") or []


def _load_by_number(invoice_number: str, fallback_name: str) -> bytes | None:
    for case in _manifest_cases():
        if case.get("number") == invoice_number:
            return _load(case["filename"])
    return _load(fallback_name)


@pytest.mark.parametrize("case", _manifest_cases(), ids=lambda case: case["filename"])
def test_manifest_samples_parse_core_fields(case: dict) -> None:
    content = _load(case["filename"])
    if content is None:
        pytest.skip(f"样本缺失: {case['filename']}（属正常，docs/sample 不入库）")

    data = parse_invoice(content)
    assert data["invoice_type"] == case["kind"]
    assert data["invoice_number"] == case["number"]
    assert data["issue_date"]
    assert data["source"]["format"] == "pdf"
    assert data["source"]["extracted_by"] == "text_layer"

    if case["kind"] == "rail_12306":
        assert data["document_type"] == "pdf-rail-12306"
        rail = data["extra"]["rail_12306"]
        assert data["amount_with_tax"]
        assert data["items"]
        assert rail["train_no"]
        assert rail["from_station"]
        assert rail["to_station"]
        assert rail["depart_time"]
        assert rail["seat_type"]
    else:
        assert data["document_type"] == "pdf-fapiao"
        assert data["buyer"]["name"]
        assert data["seller"]["name"]
        assert data["amount_with_tax"]
        assert data["items"]


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
    content = _load_by_number(expected["invoice_number"], filename)
    if content is None:
        pytest.skip(f"样本缺失: {filename}（属正常，docs/sample 不入库）")

    data = parse_invoice(content)
    assert data["document_type"] == "pdf-fapiao"
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


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "专票1.pdf",
            {
                "invoice_number": "26317000001678029323",
                "issue_date": "2026-05-08",
                "buyer_name": "浙江捷发科技股份有限公司",
                "seller_name": "上海圆迈贸易有限公司",
                "amount_without_tax": "34.67",
                "tax_amount": "4.51",
                "amount_with_tax": "39.18",
            },
        ),
        (
            "专票2.pdf",
            {
                "invoice_number": "25922000000084730813",
                "issue_date": "2025-12-25",
                "buyer_name": "浙江捷发科技股份有限公司",
                "seller_name": "青岛易来智能科技股份有限公司",
                "amount_without_tax": "984.08",
                "tax_amount": "127.92",
                "amount_with_tax": "1112.00",
            },
        ),
        (
            "专票3.pdf",
            {
                "invoice_number": "25422000000141332964",
                "issue_date": "2025-08-01",
                "buyer_name": "浙江捷发科技股份有限公司",
                "seller_name": "凯漫达(襄阳)酒店管理有限公司",
                "amount_without_tax": "267.40",
                "tax_amount": "2.67",
                "amount_with_tax": "270.07",
            },
        ),
    ],
)
def test_digital_special_real_sample(filename: str, expected: dict) -> None:
    content = _load_by_number(expected["invoice_number"], filename)
    if content is None:
        pytest.skip(f"样本缺失: {filename}（属正常，docs/sample 不入库）")

    data = parse_invoice(content)
    assert data["document_type"] == "pdf-fapiao"
    assert data["invoice_type"] == "digital_special"
    assert data["invoice_number"] == expected["invoice_number"]
    assert data["issue_date"] == expected["issue_date"]
    assert data["buyer"]["name"] == expected["buyer_name"]
    assert data["seller"]["name"] == expected["seller_name"]
    assert data["amount_without_tax"] == expected["amount_without_tax"]
    assert data["tax_amount"] == expected["tax_amount"]
    assert data["amount_with_tax"] == expected["amount_with_tax"]
    assert data["buyer"]["tax_id"]
    assert data["seller"]["tax_id"]
    assert data["items"]
    assert data["source"]["extracted_by"] == "text_layer"


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            "12306-1.pdf",
            {
                "invoice_number": "25429122450000014308",
                "issue_date": "2025-08-08",
                "amount_with_tax": "396.00",
                "train_no": "G3123",
                "from_station": "黄冈东",
                "to_station": "南京南",
                "depart_time": "2025-03-21 13:53:00",
                "seat_type": "一等座",
            },
        ),
        (
            "12306-2pdf.pdf",
            {
                "invoice_number": "25429265812000013020",
                "issue_date": "2025-08-08",
                "amount_with_tax": "2.00",
                "train_no": "G1140",
                "from_station": "岳阳东",
                "to_station": "武汉",
                "depart_time": "2025-03-20 18:05:00",
                "seat_type": "二等座",
            },
        ),
    ],
)
def test_rail_12306_real_sample(filename: str, expected: dict) -> None:
    content = _load_by_number(expected["invoice_number"], filename)
    if content is None:
        pytest.skip(f"样本缺失: {filename}（属正常，docs/sample 不入库）")

    data = parse_invoice(content)
    rail = data["extra"]["rail_12306"]
    assert data["document_type"] == "pdf-rail-12306"
    assert data["invoice_type"] == "rail_12306"
    assert data["invoice_number"] == expected["invoice_number"]
    assert data["issue_date"] == expected["issue_date"]
    assert data["buyer"]["name"] == "浙江捷发科技股份有限公司"
    assert data["buyer"]["tax_id"]
    assert data["amount_with_tax"] == expected["amount_with_tax"]
    assert rail["passenger_name"]
    assert rail["id_no_masked"]
    assert rail["train_no"] == expected["train_no"]
    assert rail["from_station"] == expected["from_station"]
    assert rail["to_station"] == expected["to_station"]
    assert rail["depart_time"] == expected["depart_time"]
    assert rail["seat_type"] == expected["seat_type"]
    assert data["items"][0]["amount"] == expected["amount_with_tax"]
