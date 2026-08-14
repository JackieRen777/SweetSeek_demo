"""Create a review packet from a retrieval report without modifying gold labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_review_packet(report: dict) -> dict:
    items = []
    seen_questions = set()
    for detail in report.get("details", []):
        question_id = detail.get("question_id")
        if not question_id or question_id in seen_questions:
            continue
        seen_questions.add(question_id)
        pipeline = detail.get("pipeline", {})
        documents = []
        seen_documents = set()
        for chunk in pipeline.get("chunks", []):
            document_id = chunk.get("document_id")
            if not document_id or document_id in seen_documents:
                continue
            seen_documents.add(document_id)
            documents.append(
                {
                    "document_id": document_id,
                    "filename": chunk.get("filename"),
                    "best_rank": chunk.get("rank"),
                    "best_score": chunk.get("score"),
                    "relevant": None,
                    "relevance": None,
                    "review_note": "",
                }
            )
            if len(documents) == 10:
                break
        evidence = [
            {
                "chunk_id": chunk.get("chunk_id"),
                "document_id": chunk.get("document_id"),
                "filename": chunk.get("filename"),
                "page": chunk.get("page"),
                "section": chunk.get("section"),
                "rank": chunk.get("rank"),
                "score": chunk.get("score"),
                "quote": chunk.get("text", ""),
                "supports_answer": None,
                "review_note": "",
            }
            for chunk in pipeline.get("chunks", [])[:20]
        ]
        items.append(
            {
                "question_id": question_id,
                "question": detail.get("question"),
                "candidate_documents": documents,
                "candidate_evidence": evidence,
            }
        )
    return {
        "schema_version": "1.0",
        "source_report": report.get("created_at"),
        "instructions": "Set relevant/supports_answer and notes. A domain reviewer must transfer confirmed labels into the gold set.",
        "items": items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a SweetSeek RAG annotation review packet")
    parser.add_argument("report")
    parser.add_argument("output")
    args = parser.parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    packet = build_review_packet(report)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Review packet: {destination} ({len(packet['items'])} questions)")


if __name__ == "__main__":
    main()
