#!/usr/bin/env python3
from adapter_common import run_dataset, write_contract_docs, write_feasibility_review


if __name__ == "__main__":
    write_contract_docs()
    write_feasibility_review()
    run_dataset("e60")
