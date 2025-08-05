#!/bin/bash
# submit_all.sh — Submit jobs in all defect folders except those starting with "z"

for dir in */; do
  name="${dir%/}"
  if [[ "$name" != z* ]] && [[ -f "$dir/job.justhpc" ]]; then
    echo "🔁 Submitting in $name..."
    (cd "$dir" && sbatch job.justhpc)
  else
    echo "⏭️ Skipping $name"
  fi
done
