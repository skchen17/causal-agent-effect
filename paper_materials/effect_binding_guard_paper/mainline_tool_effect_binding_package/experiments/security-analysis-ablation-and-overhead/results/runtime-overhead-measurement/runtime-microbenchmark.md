# E83 Hardened Runtime Microbenchmark

Status: `passed`.

| Fields | Ledger noise | p50 wall (us) | p95 wall (us) | p50 CPU (us) |
|---:|---:|---:|---:|---:|
| 1 | 0 | 22.050 | 23.112 | 21.455 |
| 2 | 0 | 31.231 | 31.762 | 30.620 |
| 4 | 0 | 46.531 | 47.031 | 45.890 |
| 8 | 0 | 74.612 | 75.812 | 73.940 |
| 16 | 0 | 132.104 | 133.155 | 131.380 |
| 32 | 0 | 244.686 | 249.649 | 243.850 |
| 1 | 16 | 51.412 | 52.002 | 50.730 |
| 2 | 16 | 58.991 | 59.502 | 58.280 |
| 4 | 16 | 73.852 | 74.522 | 73.150 |
| 8 | 16 | 101.943 | 102.933 | 101.180 |
| 16 | 16 | 158.864 | 162.676 | 158.065 |
| 32 | 16 | 270.673 | 275.767 | 269.820 |
| 1 | 64 | 132.154 | 136.704 | 131.420 |
| 2 | 64 | 140.034 | 144.367 | 139.280 |
| 4 | 64 | 154.645 | 158.857 | 153.845 |
| 8 | 64 | 183.305 | 188.166 | 182.480 |
| 16 | 64 | 239.297 | 244.207 | 238.490 |
| 32 | 64 | 352.030 | 357.600 | 351.125 |

## Claim Boundary

This is an in-process CPU microbenchmark of the pure hardened precommit kernel. It excludes model, sandbox, canonicalization I/O, user simulation, and end-to-end trajectory latency; final E83 must report those separately.
