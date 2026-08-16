#!/usr/bin/env python3
from external_trace_common import run_discovery, run_leakage, run_normalize, run_raw_manifest, write_annotation_guide


if __name__ == "__main__":
    run_discovery()
    write_annotation_guide()
    cases = run_normalize()
    run_raw_manifest(cases)
    run_leakage()
