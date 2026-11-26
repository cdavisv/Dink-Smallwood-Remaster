#!/usr/bin/env bash
# usage: tools/coord/merge_pr2.sh <pr>
# Merges a PR only when: it is mergeable (an AGENTS.md-only conflict is resolved by merge_master_docs.sh first; any other
# conflict stops), the CI source-audit check passed, no commit carries an attribution (Co-Authored-By) line, the private
# check of its files (lfs_private_check.sh on origin/<branch>) has 0 hits, and the CI lfs-private-check passed when it ran.
# "merged" is printed only when GitHub says the PR's state is MERGED.
# Docs-only PRs: the source-audit workflow has a paths filter, so a PR that touches no file under its trigger paths gets
# no source-audit check at all. When the PR's file list (from GitHub) has no file under those paths and every file is a
# Markdown file (*.md), the missing check counts as a pass; any other PR without the check is not merged (exit 4).
# Env: DINK_REPO (default: the origin remote's owner/name).
set -uo pipefail
pr=${1:?usage: merge_pr2.sh <pr>}
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git -C "$HERE" rev-parse --show-toplevel)" || exit 2
R=${DINK_REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}
WF=.github/workflows/unreal-source-audit.yml
B=$(gh pr view "$pr" --repo "$R" --json headRefName --jq .headRefName) || { echo "#$pr: no such PR"; exit 2; }

# Trigger paths of the source-audit workflow (the pull_request 'paths:' list), as shell globs.
triggers(){ git show "origin/master:$WF" | awk '/^  pull_request:/{p=1;next} p&&/^  [a-z_]+:/{p=0} p&&/^      - /{sub(/^      - /,""); gsub(/\047/,""); print}'; }
# 0 = the source-audit workflow is not expected to run on this PR (docs only), 1 = it must run, 2 = not docs only.
expect_audit(){
  local files f t hit=0 md=1
  files=$(gh pr view "$pr" --repo "$R" --json files --jq '.files[].path') || return 1
  [ -n "$files" ] || return 1
  while IFS= read -r f; do
    while IFS= read -r t; do
      # shellcheck disable=SC2053
      case "$t" in *'/**') [[ "$f" == "${t%/**}/"* ]] && hit=1;; *) [[ "$f" == $t ]] && hit=1;; esac
    done < <(triggers)
    [[ "$f" == *.md ]] || md=0
  done <<<"$files"
  [ $hit = 1 ] && return 1
  [ $md = 1 ] && return 0
  return 2
}
check_state(){ gh pr checks "$pr" --repo "$R" 2>/dev/null | awk -v n="$1" '$1==n{print $2}' | head -1; }

for try in 1 2 3; do
  git fetch -q origin
  until m=$(gh pr view "$pr" --repo "$R" --json mergeable --jq .mergeable) && [ "$m" != "UNKNOWN" ]; do sleep 3; done
  if [ "$m" = CONFLICTING ]; then
    o=$("$HERE/merge_master_docs.sh" "$B" 2>&1); rc=$?; echo "$o" | tail -2
    [ $rc = 0 ] || { echo "#$pr: NOT merged, conflict outside AGENTS.md"; exit 3; }
    sleep 8; continue
  fi
  expect_audit; ea=$?
  if [ $ea = 0 ]; then
    echo "#$pr: docs-only (every file *.md, none under the source-audit paths): no source-audit check expected, counted as pass"
  elif [ $ea = 2 ]; then
    s=$(check_state source-audit)
    [ "$s" = pass ] || { echo "#$pr: NOT merged, no source-audit check and the PR is not docs-only"; exit 4; }
  else
    until s=$(check_state source-audit) && [ -n "$s" ] && [ "$s" != "pending" ]; do sleep 5; done
    [ "$s" = pass ] || { echo "#$pr: NOT merged, source-audit $s"; exit 4; }
  fi
  lp=$(check_state lfs-private-check)
  while [ "$lp" = pending ]; do sleep 5; lp=$(check_state lfs-private-check); done
  [ -z "$lp" ] || [ "$lp" = pass ] || [ "$lp" = skipping ] || { echo "#$pr: NOT merged, CI lfs-private-check $lp"; exit 6; }
  git fetch -q origin
  a=$(git log --format=%B "origin/master..origin/$B" | grep -c -i 'co-authored')
  [ "$a" = 0 ] || { echo "#$pr: NOT merged, attribution line found"; exit 5; }
  timeout 600 "$HERE/lfs_private_check.sh" "origin/$B" | tail -1 | grep -q "private hits: 0" || { echo "#$pr: NOT merged, private hits or check timeout"; exit 6; }
  out=$(gh pr merge "$pr" --repo "$R" --merge --subject "Merge pull request #$pr from ${R%%/*}/$B" 2>&1)
  st=$(gh pr view "$pr" --repo "$R" --json state --jq .state)
  if [ "$st" = MERGED ]; then git fetch -q origin; echo "#$pr merged: $(git log --oneline -1 origin/master | cut -c1-70)"; exit 0; fi
  echo "#$pr: try $try not merged (state $st): $(echo "$out" | grep -v '^hint\|^  - ' | tail -1)"; sleep 5
done
echo "#$pr: NOT merged after 3 tries"; exit 7
