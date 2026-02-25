from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from evidence_ranker import EvidenceRanker
from logger import setup_logger
from query_expander import SweetnessQueryExpander
from services.llm_client import DeepSeekLLMClient
from services.compound_service import CompoundService


@dataclass
class Services:
    query_expander: SweetnessQueryExpander
    evidence_ranker: EvidenceRanker
    llm_client: Optional[DeepSeekLLMClient]
    compound_service: CompoundService


def build_services() -> Services:
    logger = setup_logger("sweetseek")
    query_expander = SweetnessQueryExpander()
    evidence_ranker = EvidenceRanker()
    compound_service = CompoundService()

    llm_client = None
    import persistent_storage
    if hasattr(persistent_storage, "configure_llm"):
        persistent_storage.configure_llm()
    if hasattr(persistent_storage, "deepseek_client") and hasattr(persistent_storage, "deepseek_model"):
        llm_client = DeepSeekLLMClient(persistent_storage.deepseek_client, persistent_storage.deepseek_model)
    else:
        logger.warning("DeepSeek client 未配置，LLM功能将不可用")

    return Services(
        query_expander=query_expander,
        evidence_ranker=evidence_ranker,
        llm_client=llm_client,
        compound_service=compound_service,
    )
