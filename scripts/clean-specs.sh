#!/usr/bin/env bash
# Sync the current branch from main while keeping only the matching spec folder.
#
# Usage:
#   scripts/clean-specs.sh [source-ref]
#
# Examples:
#   scripts/clean-specs.sh
#   scripts/clean-specs.sh origin/main
#
# Behavior:
# - Restores the working tree from the source ref
# - Keeps only specs/<current-branch>/ after restore
# - Removes every other specs/<phase>/ folder
# - Creates a commit only if there are staged changes

set -euo pipefail

source_ref="${1:-main}"
branch="$(git branch --show-current)"

if [[ -z "$branch" ]]; then
  echo "Error: not on a branch" >&2
  exit 1
fi

if ! git rev-parse --verify "$source_ref" >/dev/null 2>&1; then
  if [[ "$source_ref" == "main" ]] && git rev-parse --verify origin/main >/dev/null 2>&1; then
    source_ref="origin/main"
  else
    echo "Error: source ref '$source_ref' not found" >&2
    exit 1
  fi
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree has uncommitted changes. Commit or stash first." >&2
  exit 1
fi

echo "Syncing branch '$branch' from '$source_ref'"

# Restore everything from the source ref, including the matching spec folder.
git restore --source="$source_ref" -- .

# Remove other spec folders so only the current branch spec remains.
for spec_dir in specs/*/; do
  [[ -d "$spec_dir" ]] || continue
  spec_name="$(basename "$spec_dir")"
  if [[ "$spec_name" != "$branch" ]]; then
    git rm -rf --cached --ignore-unmatch "$spec_dir" >/dev/null 2>&1 || true
    rm -rf "$spec_dir"
  fi
done

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit"
  exit 0
fi

git commit -m "chore: sync branch from $source_ref while keeping only $branch spec"
