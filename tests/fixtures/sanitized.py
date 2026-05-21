"""脱敏测试数据。

这里的数据全部为人工合成，不来源于真实发票样本。PDF parser 测试通过 monkeypatch
注入这些文本，OFD 测试使用最小 ZIP/XML 容器生成。
"""

from __future__ import annotations

import zipfile
from io import BytesIO

DIGITAL_GENERAL_TEXT = """电子发票(普通发票)
发票号码: 26100000000000000001
开票日期: 2026年05月17日
购买方信息 销售方信息
名 称: 测试采购科技有限公司 名 称: 脱敏销售服务有限公司
统一社会信用代码/纳税人识别号: 91110000000000001A 统一社会信用代码/纳税人识别号: 92220000000000002B
项目名称 规格型号 单位 数量 单价 金额 税率/征收率 税额
*信息技术服务*测试服务 199.06 6% 11.94
合 计 ¥199.06 ¥11.94
价税合计(大写) 贰佰壹拾壹圆整 (小写) ¥211.00
开票人: 测试员
"""


DIGITAL_GENERAL_TAX_FREE_TEXT = """电子发票(普通发票)
发票代码:033002100111
发票号码: 12345678
开票日期: 2024 年 07 月 03日
名 称: 脱敏买方有限公司 名 称: 脱敏免税商店
统一社会信用代码/纳税人识别号: 91330000000000003C 统一社会信用代码/纳税人识别号: 91330000000000004D
项目名称 规格型号 单位 数量 单价 金额 税率/征收率 税额
*农产品*测试商品 139.50 免税 *
合 计 ¥139.50 *
价税合计(大写) 壹佰叁拾玖圆伍角 (小写) ¥139.50
"""


DIGITAL_SPECIAL_TEXT = """电子发票(增值税专用发票)
发票号码: 26100000000000000002
开票日期: 2026年05月08日
名 称: 脱敏采购设备有限公司 名 称: 脱敏贸易有限公司
统一社会信用代码/纳税人识别号: 91440000000000005E 统一社会信用代码/纳税人识别号: 91440000000000006F
项目名称 规格型号 单位 数量 单价 金额 税率/征收率 税额
*电子产品*测试配件 34.67 13% 4.51
合 计
¥34.67 ¥4.51
价税合计(大写) 叁拾玖圆壹角捌分 (小写) ¥39.18
开票人: 专票员
"""


DIGITAL_SPECIAL_BARE_TEXT = """电子发票(增值税专用发票)
26100000000000000003
2025年08月01日
脱敏买方工程有限公司 脱敏卖方酒店有限公司
91420000000000007G 91420000000000008H
项目名称 规格型号 单位 数量 单价 金额 税率/征收率 税额
住宿服务测试项目
267.40 1% 2.67
合 计 ¥267.40 ¥2.67
价税合计(大写) 贰佰柒拾圆零柒分 (小写) ¥270.07
"""


RAIL_12306_TEXT = """中国铁路电子客票
发票号码:25420000000000000001
开票日期:2025年08月08日
购买方名称:脱敏采购科技有限公司 统一社会信用代码:91110000000000001A
电子客票号:E1234567890
脱敏东 G3123 脱敏南
2025年03月21日 13:53开 检票口1 一等座
110000********001X 测试乘客
¥396.00
"""


IMAGE_AIR_ITINERARY_OCR_TEXT = """航空运输电子客票行程单
旅客姓名: 测试旅客
证件号码: 110000********001X
电子客票号码: 7812345678901
航班号: CA1234
承运人: CA
舱位: Y
出发站: 脱敏机场
到达站: 测试机场
开票日期: 2025年07月04日
票价: 550.46
燃油附加费: 9.17
民航发展基金: 50.00
合计: 610.46
"""


AIR_ITINERARY_FIELDS = {
    "ElectronicInvoiceAirTransportReceiptNumber": "AIR000000000001",
    "IssueDate": "2025-07-04",
    "CarrierDate": "2025-07-05",
    "DepartureTime": "08:15",
    "Fare": "550.46",
    "VatTaxAmount": "49.54",
    "TotalAmount": "610.46",
    "PassengerName": "测试旅客",
    "ValidIdNumber": "110000********001X",
    "ETicketNumber": "7812345678901",
    "Flight": "CA1234",
    "Carrier": "CA",
    "Class": "Y",
    "DepartureStation": "脱敏机场",
    "DestinationStation": "测试机场",
    "FuelSurcharge": "9.17",
    "CivilAviationDevelopmentFund": "50.00",
    "OtherTaxes": "0.00",
    "VatRate": "0.09",
    "NameOfSeller": "脱敏航空有限公司",
    "UnifiedSocialCreditCodeOfSeller": "91110000000000009J",
    "NameOfPurchaser": "脱敏采购科技有限公司",
    "UnifiedSocialCreditCodeOfPurchaser": "91110000000000001A",
    "VerificationCode": "CHECK000001",
}


def make_ofd_air_itinerary(fields: dict[str, str] | None = None) -> bytes:
    values = {**AIR_ITINERARY_FIELDS, **(fields or {})}
    return _make_ofd_zip(
        {
            "OFD.xml": "<ofd></ofd>",
            "Doc_0/Attachs/atr_0.xml": _fields_xml(values),
            "Doc_0/Pages/Page_0/Content.xml": "<Page></Page>",
        }
    )


def make_ofd_invoice_text() -> bytes:
    content = """<Page>
<TextObject Boundary="0 0 100 10"><TextCode>电子发票(普通发票)</TextCode></TextObject>
<TextObject Boundary="0 20 100 10"><TextCode>发票号码:26100000000000000004</TextCode></TextObject>
</Page>"""
    return _make_ofd_zip({"OFD.xml": "<ofd></ofd>", "Doc_0/Pages/Page_0/Content.xml": content})


def make_ofd_unknown() -> bytes:
    return _make_ofd_zip(
        {
            "OFD.xml": "<ofd></ofd>",
            "Doc_0/Pages/Page_0/Content.xml": (
                '<Page><TextObject Boundary="0 0 100 10">'
                "<TextCode>普通文档</TextCode></TextObject></Page>"
            ),
        }
    )


def _make_ofd_zip(files: dict[str, str | bytes]) -> bytes:
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return bio.getvalue()


def _fields_xml(fields: dict[str, str]) -> str:
    parts = ["<Root>"]
    for key, value in fields.items():
        parts.append(f"<{key}>{_xml_escape(value)}</{key}>")
    parts.append("</Root>")
    return "".join(parts)


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
