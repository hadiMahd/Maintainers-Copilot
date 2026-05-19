#!/usr/bin/env bash
# Remove spec folders that don't belong to the current branch.
# Run manually or install as a post-merge hook:
#   cp scripts/clean-specs.sh .git/hooks/post-merge && chmod +x .git/hooks/post-merge

branch=$(git branch --show-current)
changed=false

for spec_dir in specs/*/; do
  [[ -d "$spec_dir" ]] || continue
  spec_name=$(basename "$spec_dir")
  if [[ "$spec_name" != "$branch" ]]; then
    git rm -rf --cached --ignore-unmatch "specs/$spec_name/" > /dev/null 2>&1
    rm -rf "specs/$spec_name/"
    changed=true
  fi
done

if [[ "$changed" == "true" ]] && ! git diff --cached --quiet; then
  git commit -m "chore: remove other phase specs after merge" --no-edit
fi
