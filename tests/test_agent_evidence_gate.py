"""Evidence-gate contract tests for the Agent and OpenClaw layers.

These tests are deliberately database- and network-free.  They protect the
boundary between verified internal calculations, conditional candidates,
official policy evidence, and unverified web-search clues.
"""

from __future__ import annotations

from app.agent.graph import _apply_final_evidence_gate, _evidence_gate
from app.agent.prompts import EVIDENCE_GATE_SHORT, SYSTEM_PROMPT
from app.services.openclaw_client import (
    _openclaw_evidence_gate,
    _openclaw_tool_payload,
    _prepare_request_messages,
)


def _complete_cbu() -> dict:
    return {
        "applicability_status": "FULL_RESULT",
        "combined_results": [
            {
                "regime_label": "MFN",
                "effective_tax_rate": "0.2715",
                "is_complete": True,
            },
            {
                "regime_label": "ACFTA",
                "effective_tax_rate": "0.2715",
                "is_complete": True,
            },
        ],
        "evidence_refs": [{"evidence_id": "RULE-MY-001"}],
    }


def test_complete_internal_calculator_is_the_numeric_authority() -> None:
    gate = _evidence_gate("calculate_cbu_tax", _complete_cbu())

    assert gate["source_tier"] == "INTERNAL_VERIFIED"
    assert gate["can_confirm_numeric_rates"] is True
    assert gate["candidate_only"] is False
    assert gate["web_search_may_override"] is False


def test_candidate_and_search_results_cannot_establish_a_rate() -> None:
    candidate = _evidence_gate(
        "calculate_cbu_tax",
        {
            "applicability_status": "CANDIDATE_REGIMES",
            "import_duty_options": [{"rate": "0"}],
        },
    )
    web = _openclaw_evidence_gate(
        "gais_web_search",
        {"status": "OK", "results": [{"title": "snippet", "url": "https://example.test"}]},
    )

    assert candidate["semantic_status"] == "CANDIDATE_CONDITIONAL"
    assert candidate["candidate_only"] is True
    assert candidate["can_confirm_numeric_rates"] is False
    assert candidate["zero_rate_is_not_total_burden"] is True
    assert web["source_tier"] == "EXTERNAL_UNVERIFIED"
    assert web["can_confirm_numeric_rates"] is False
    assert web["web_search_may_override"] is False


def test_status_semantics_are_not_collapsed() -> None:
    from app.agent.graph import _semantic_result_status

    assert _semantic_result_status("calculate_cbu_tax", {"status": "UNSUPPORTED_COUNTRY"}) == "NOT_APPLICABLE"
    assert _semantic_result_status(
        "calculate_cbu_tax", {"status": "CLASSIFICATION_SELECTION_REQUIRED"}
    ) == "PENDING_CLASSIFICATION"
    assert _semantic_result_status(
        "calculate_cbu_tax", {"status": "NOT_FOUND"}
    ) == "NOT_IN_DATABASE"


def test_incomplete_rate_answer_gets_visible_evidence_warning() -> None:
    state = {
        "tool_results": {
            "run-1": {
                "tool_name": "gais_web_search",
                "result": {"status": "OK", "results": [{"url": "https://example.test"}]},
            }
        }
    }
    answer = _apply_final_evidence_gate(
        "搜索摘要称某方案为0%，但需要进一步确认。",
        state,
        "2027年税率是多少？",
    )

    assert answer.startswith("⚠️ 证据门禁")
    assert "不等于综合税负" in answer


def test_openclaw_receives_gate_once_and_tool_name() -> None:
    messages = [{"role": "system", "content": "base"}, {"role": "user", "content": "税率是多少？"}]
    prepared = _prepare_request_messages(messages)
    prepared_again = _prepare_request_messages(prepared)

    assert sum("AUTOPOLICY_EVIDENCE_GATE_V1" in str(item.get("content")) for item in prepared) == 1
    assert len(prepared_again) == len(prepared)
    payload = _openclaw_tool_payload("gais_web_search", {"status": "OK", "results": []})
    assert '"tool_name": "gais_web_search"' in payload
    assert '"source_tier": "EXTERNAL_UNVERIFIED"' in payload


def test_prompt_contract_mentions_the_required_layers() -> None:
    prompt = SYSTEM_PROMPT + EVIDENCE_GATE_SHORT
    for phrase in ("未入库", "未匹配", "待归类", "不适用", "零关税", "98.49"):
        assert phrase in prompt
