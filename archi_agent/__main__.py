import argparse
import json
from pathlib import Path

from .agent import extractive_answer, run_agent
from .retrieval import KnowledgeBase

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="ArchiEvidence 建筑学习笔记检索与工具 Agent")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "knowledge.sqlite3")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("index")
    ingest.add_argument("directory", nargs="?", type=Path, default=ROOT / "sample_notes")
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--online", action="store_true")
    args = parser.parse_args()
    knowledge = KnowledgeBase(args.db)
    try:
        if args.command == "index":
            result = knowledge.index(args.directory)
        elif args.online:
            from .client import ChatClient
            result = run_agent(args.question, knowledge, ChatClient())
        else:
            result = extractive_answer(args.question, knowledge)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f"错误：{error}\n")


if __name__ == "__main__":
    main()
