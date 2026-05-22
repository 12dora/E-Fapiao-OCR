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


DIGITAL_GENERAL_STACKED_VALUES_TEXT = """电子发票(普通发票) 发票号码:
开票日期:
购
买
方
信
息
统一社会信用代码/纳税人识别号:
销
售
方
信
息
统一社会信用代码/纳税人识别号:
名称: 名称:
项目名称 规格型号 单 位 数 量 单 价 金 额 税率/征收率 税 额
合 计
价税合计(大写) (小写)
备
注
开票人:
26100000000000000005
2026年05月06日
脱敏采购科技有限公司
91110000000000001A
脱敏销售服务有限公司
92220000000000002B
¥776.24 ¥7.76
柒佰捌拾肆圆整 ¥784.00
测试员
测试员
*餐饮服务*餐饮服务 776.24 1% 7.76
"""


DIGITAL_GENERAL_STACKED_TAX_FREE_TEXT = """电子发票(普通发票) 发票号码:
开票日期:
购买方信息
统一社会信用代码/纳税人识别号:
销售方信息
统一社会信用代码/纳税人识别号:
名称: 名称:
项目名称 规格型号 单 位 数 量 单 价 金 额 税率/征收率 税 额
合 计
价税合计(大写) (小写)
开票人:
26100000000000000006
2026年05月02日
脱敏采购科技有限公司
91110000000000001A
脱敏免税服务中心
12330000MB00000001
¥300.00 ***
叁佰圆整 ¥300.00
测试员
*文化服务*参观券
张 5 60 300.00 免税 ***
"""


DIGITAL_GENERAL_TOLL_TEXT = """电子发票(普通发票)
发票号码:
开票日期:
购买方信息
统一社会信用代码/纳税人识别号:
销售方信息
统一社会信用代码/纳税人识别号:
名称:
名称:
项目名称 车牌号 车辆类型 通行日期起 通行日期止 金额 税率/征收率 税额
合 计
价税合计(大写) (小写)
开票人:
26327902540500062081 2026年05月05日 91330600597214350R
脱敏高速公路有限公司91320506743132004F *经营租赁*通行费 浙A00000 客车
20260430 34.38 3% 1.03 ¥34.38 叁拾伍圆肆角壹分 测试员 ¥35.41 20260430 脱敏采购科技有限公司 ¥1.03
"""


DIGITAL_GENERAL_STANDALONE_PRICE_TAX_TEXT = """电子发票(普通发票)
发票号码:26337000000454161517
开票日期:2026年05月06日
脱敏采购科技有限公司 脱敏保险服务有限公司
91330600597214350R 91330000000000002B
项目名称 规格型号 单 位 数 量 单 价 金 额 税率/征收率 税 额
*保险服务*车辆商业保险
6839.07 6% 410.34
合 计
价税合计(大写) (小写)
¥6839.07 ¥410.34
¥7249.41
车牌号浙A00000
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


IMAGE_AIR_ITINERARY_CNOCR_TEXT = """发聚华动
电子发票
烧空运输
比希客票行程单)
国内国际标识：国内
发票号码: 25138836112000777382
旅客姓名
有效身份证件号码
签注
测试旅客
110000********001X
不得签转/更改退票收费
承运人
航班号
座位等级
日期
时间
客票级别/客票类别
客票生效日期|有效截止日期免费行李
自：脱敏机场T3
CA
CA1234
Y
2025年07月05日
08:15
Y
20K
至:测试机场T2
票价
燃油附加费
增值税税率
增值税税额
民航发展基金
其他税费
合计
CNY 550.46
CNY 9.17
9%
CNY 49.54
CNY 50.00
CNY 0.00
CNY 610.46
电子客票号码:7812345678901
验证码:CHECK000001
销售网点代号:TEST001
填开单位:脱敏航空服务有限公司
填开日期:2025年07月04日
购买方名称:脱敏采购科技有限公司
统一社会信用代码/纳税人识别号:91110000000000001A
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
