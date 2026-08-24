"""Tool: get_policy_evidence — retrieves original clause text, translation, and official link.

Directly calls the Repository (not HTTP), using clause_id to locate the specific legal provision,
not just the whole document.
"""

from __future__ import annotations

from langchain_core.tools import tool
from sqlalchemy import text

from app.agent.guard import sanitize_evidence_text
from app.db.session import SessionLocal


@tool
def get_policy_evidence(clause_id: str) -> dict:
    """Retrieve the original text, Chinese translation, and official link for a specific
    legal clause or policy provision that supports a tax rule or incentive decision.

    clause_id is the source_clause primary key — it pinpoints the exact legal provision,
    not the entire document. Found in search_policy_rules results under evidence[].clause_id.
    """
    db = SessionLocal()
    try:
        row = db.execute(
            text("""
                SELECT
                  clause.source_clause_id AS clause_id,
                  doc.source_document_id AS document_id,
                  doc.document_title,
                  doc.document_number,
                  doc.source_type,
                  doc.canonical_url AS official_url,
                  auth.authority_name,
                  clause.locator_type,
                  clause.locator_value,
                  clause.original_text,
                  clause.translated_text_cn,
                  clause.evidence_summary
                FROM evidence.source_clause clause
                JOIN evidence.source_document doc
                  ON doc.source_document_id = clause.source_document_id
                LEFT JOIN ref.authority auth
                  ON auth.authority_id = doc.authority_id
                WHERE clause.source_clause_id = :clause_id
            """),
            {"clause_id": clause_id},
        ).mappings().first()

        if row is None:
            return {"status": "NOT_FOUND", "clause_id": clause_id}

        return {
            "status": "FOUND",
            "clause_id": str(row["clause_id"]),
            "document_id": str(row["document_id"]),
            "document_title": row["document_title"] or "",
            "document_number": row["document_number"],
            "source_type": row["source_type"] or "",
            "authority_name": row["authority_name"] or "",
            "official_url": row["official_url"],
            "locator_type": row["locator_type"] or "",
            "locator_value": row["locator_value"] or "",
            "evidence_summary": row["evidence_summary"] or "",
            "original_text": sanitize_evidence_text(row["original_text"] or ""),
            "translated_text_cn": sanitize_evidence_text(row["translated_text_cn"] or ""),
        }

    finally:
        db.close()
