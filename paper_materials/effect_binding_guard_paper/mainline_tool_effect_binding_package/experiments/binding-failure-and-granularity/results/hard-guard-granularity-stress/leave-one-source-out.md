# E50 Leave-One-Source-Out

## Aggregate

{
  "unsafe_pre_allow": {
    "mean": 0.04671717171717172,
    "median": 0.015151515151515152,
    "min": 0.0,
    "max": 0.125,
    "n": 3
  },
  "safe_false_deny": {
    "mean": 0.047979797979797977,
    "median": 0.06060606060606061,
    "min": 0.0,
    "max": 0.08333333333333333,
    "n": 3
  },
  "coverage": {
    "mean": 0.8708754208754209,
    "median": 0.8916666666666667,
    "min": 0.7777777777777778,
    "max": 0.9431818181818182,
    "n": 3
  },
  "abstain_rate": {
    "mean": 0.12912457912457911,
    "median": 0.10833333333333334,
    "min": 0.056818181818181816,
    "max": 0.2222222222222222,
    "n": 3
  }
}

## Splits

- `strict_loso_camel`: UPA `0.000`, FDeny `0.000`, coverage `0.778`.
- `strict_loso_ipiguard`: UPA `0.125`, FDeny `0.083`, coverage `0.892`.
- `strict_loso_phase4`: UPA `0.015`, FDeny `0.061`, coverage `0.943`.
