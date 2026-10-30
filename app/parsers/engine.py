import logging
from typing import List, Optional
from app.core.models import NormalizedLog
from app.parsers.base import BaseParser
from app.parsers.huawei import HuaweiParser
from app.parsers.nokia import NokiaParser
from app.parsers.zte import ZTEParser
from app.parsers.juniper import JuniperParser
from app.parsers.cisco import CiscoParser
from app.parsers.generic import GenericParser

logger = logging.getLogger("NetLogIQ.ParserEngine")

class ParserEngine:
    def __init__(self):
        # Order of parsers: specialized first, generic last
        self.parsers: List[BaseParser] = [
            HuaweiParser(),
            NokiaParser(),
            ZTEParser(),
            JuniperParser(),
            CiscoParser(),
            GenericParser(),  # Fallback
        ]

    def parse(self, raw_message: str, source_ip: str) -> NormalizedLog:
        """
        Attempt to parse log using vendor-specific parsers.
        Guaranteed to return a NormalizedLog (using GenericParser if needed).
        """
        for parser in self.parsers:
            try:
                if parser.can_parse(raw_message):
                    log = parser.parse(raw_message, source_ip)
                    if log:
                        return log
            except Exception as e:
                logger.debug(f"Parser {parser.vendor_name} failed on message: {e}")
                continue

        # Ultimate fallback
        return GenericParser().parse(raw_message, source_ip)

# Global parser engine instance
parser_engine = ParserEngine()
