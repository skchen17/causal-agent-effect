#!/usr/bin/env bash
set -euo pipefail

EXPECTED_CASES=4590
total=0
complete_settings=0
settings=0

for file in runs/tool_effect_fragmentation_phase5/*full_cross_product.json; do
  [[ -e "${file}" ]] || continue
  cases="$(jq -r '.cases | length' "${file}")"
  complete="$(jq -r '.run_complete // false' "${file}")"
  errors="$(jq -r '.n_errors // 0' "${file}")"
  total=$((total + cases))
  settings=$((settings + 1))
  if [[ "${complete}" == "true" ]]; then
    complete_settings=$((complete_settings + 1))
  fi
  printf '%-72s cases=%-5s complete=%-5s errors=%s\n' "$(basename "${file}")" "${cases}" "${complete}" "${errors}"
done

printf '\nTotal checkpointed cases: %s/%s\n' "${total}" "${EXPECTED_CASES}"
printf 'Completed settings: %s/%s started settings\n' "${complete_settings}" "${settings}"
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
