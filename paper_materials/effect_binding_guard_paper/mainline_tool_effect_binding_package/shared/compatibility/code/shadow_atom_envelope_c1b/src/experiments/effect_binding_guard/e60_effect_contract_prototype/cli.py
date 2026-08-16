from __future__ import annotations

import argparse

from .demo import main as run_demo


def main() -> None:
    parser = argparse.ArgumentParser(description="E60 effect-contract prototype CLI.")
    parser.add_argument("--demo", action="store_true", help="Run the local stub-mode demo.")
    args = parser.parse_args()
    if args.demo:
        run_demo()
        return
    parser.error("No action selected. Use --demo.")


if __name__ == "__main__":
    main()

