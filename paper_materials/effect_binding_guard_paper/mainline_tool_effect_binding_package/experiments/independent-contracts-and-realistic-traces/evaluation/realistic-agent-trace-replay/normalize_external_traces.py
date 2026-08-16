#!/usr/bin/env python3
from external_trace_common import run_discovery, run_normalize, write_annotation_guide


if __name__ == "__main__":
    run_discovery()
    write_annotation_guide()
    run_normalize()
