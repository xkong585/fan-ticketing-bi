#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export MPLCONFIGDIR="$PWD/.mplconfig"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"${PYTHON:-python3}" src/run_pipeline.py
