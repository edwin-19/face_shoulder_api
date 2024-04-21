#!/bin/bash --login
# The --login ensures the bash configuration is loaded,

# Temporarily disable strict mode and activate conda:
set +euo pipefail
conda activate deploy_env
# enable strict mode:
set -euo pipefail

# exec the final command:
exec uvicorn app:app --port=8000 --host=0.0.0.0