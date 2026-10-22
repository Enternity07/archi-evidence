"""Small, self-authored fixture benchmark. Not a general LLM accuracy claim."""
import argparse
import json
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from archi_agent.retrieval import KnowledgeBase

ROOT = Path(__file__).resolve().parent


def evaluate():
    questions = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    rows = []
    with tempfile.TemporaryDirectory() as temp:
        knowledge = KnowledgeBase(Path(temp) / "eval.sqlite3")
        indexed = knowledge.index(ROOT / "sample_notes")
        for question in questions:
            hits = knowledge.search(question["question"], 3)
            rank = next((i for i, item in enumerate(hits, 1) if item["source"] == question["source"]), None)
            rows.append({**question, "retrieved": [item["source"] for item in hits],
                         "first_relevant_rank": rank, "no_results": not hits})
    answerable = [item for item in rows if item["source"] is not None]
    unknown = [item for item in rows if item["source"] is None]
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "mode": "offline-retrieval-only", "corpus": indexed,
            "answerable_cases": len(answerable), "unanswerable_cases": len(unknown),
            "hit_at_3": sum(item["first_relevant_rank"] is not None for item in answerable) / len(answerable),
            "mrr_at_3": sum(1 / item["first_relevant_rank"] if item["first_relevant_rank"] else 0 for item in answerable) / len(answerable),
            "unanswerable_empty_rate": sum(item["no_results"] for item in unknown) / len(unknown),
            "limitations": "15 个自建演示样例，无训练测试集隔离；不评估在线模型、语义正确性或真实用户分布。",
            "cases": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "evaluation.json")
    args = parser.parse_args()
    report = evaluate()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, ensure_ascii=False, indent=2))
