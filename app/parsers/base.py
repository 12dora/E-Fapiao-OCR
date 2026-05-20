"""Parser 抽象基类。

所有具体 Parser 必须实现 parse(content) -> RawInvoice。
RawInvoice 是中间表示，字段不要求归一化，由 Normalizer 统一处理。
"""

from abc import ABC, abstractmethod
from typing import Any


class Parser(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> dict[str, Any]:
        """返回未归一化的 RawInvoice dict。

        必须填充：
          - invoice_type: digital_general | digital_special | rail_12306
          - source.extracted_by: text_layer | qrcode | ocr
          - 其它已抽取到的原始字段
        """
        ...
