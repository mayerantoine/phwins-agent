"""CLI: `python cli.py "question"` for one-shot, or `python cli.py` for REPL.

Pass `--managed` to run against the Managed Agents runtime instead of the
local tool-use loop.
"""

import argparse

import anthropic

from phwins import ask, ask_managed, close_session, open_session
from phwins.formatting import format_answer


def _answer_local(question: str) -> None:
    try:
        result = ask(question)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(format_answer(result))


def _answer_managed(
    question: str,
    *,
    session_id: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> None:
    try:
        result = ask_managed(question, session_id=session_id, client=client)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(format_answer(result))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a question about PH WINS 2024.")
    parser.add_argument("question", nargs="?", help="Question to ask (omit for REPL).")
    parser.add_argument(
        "--managed",
        action="store_true",
        help="Use the Managed Agents runtime instead of the local tool-use loop.",
    )
    args = parser.parse_args()

    if args.managed:
        if args.question:
            _answer_managed(args.question)
            return
        client, session_id = open_session()
        print("PH WINS 2024 Q&A (Managed Agent). Type a question, or 'exit' to quit.")
        try:
            while True:
                try:
                    question = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if not question or question.lower() in {"exit", "quit"}:
                    return
                _answer_managed(question, session_id=session_id, client=client)
                print()
        finally:
            close_session(client, session_id)
        return

    if args.question:
        _answer_local(args.question)
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
        _answer_local(question)
        print()


if __name__ == "__main__":
    main()
