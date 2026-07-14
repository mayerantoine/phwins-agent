import argparse
import sys

from main import ask


def _format(result: dict) -> str:
    synthesis = (result.get("synthesis") or "").strip()
    answer = synthesis if synthesis else (result.get("direct_answer") or "").strip()

    sources = result.get("sources") or {}
    year = sources.get("survey_year", "")
    source_file = sources.get("source_file", "")
    topics = sources.get("topics") or []
    topics_str = ", ".join(topics) if topics else ""

    source_line = f"Source: PH WINS {year} ({source_file})"
    if topics_str:
        source_line += f" — topics: {topics_str}"

    return f"{answer}\n\n{source_line}"


def _answer(question: str) -> None:
    try:
        result = ask(question)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(_format(result))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about PH WINS 2024.")
    parser.add_argument("question", nargs="?", help="Question to ask (omit for REPL).")
    args = parser.parse_args()

    if args.question:
        _answer(args.question)
        return

    print("PH WINS 2024 Q&A. Type a question, or 'exit' to quit.")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question or question.lower() in {"exit", "quit"}:
            return
        _answer(question)
        print()


if __name__ == "__main__":
    main()
