#!/usr/bin/env bash
# A library release, through to a bp-sunnypilot PR (spec: ford-op/bg-opendbc#97). Bumps the library in
# bg-opendbc and merges that PR once its required checks pass (nothing else auto-merges there), then
# opens the bp-sunnypilot PR that moves opendbc_repo to the new bg-clean, saying whether it changes the
# panda firmware or the lateral Python (a drive before merge if so). Not merged automatically.
# usage: GH_TOKEN=<ford-op-sync App token for bg-opendbc and bp-sunnypilot> release_bumps.sh <tag> <commit>
set -euo pipefail
TAG=$1 SHA=$2
LIB=$(pwd)
WORK=$(mktemp -d)
git config --global user.name "ford-op-sync[bot]"
git config --global user.email "ford-op-sync[bot]@users.noreply.github.com"
# the clones have no submodules checked out: a fetch that recursed into a moved gitlink would fail
git config --global fetch.recurseSubmodules false
clone() {  # <repo> <branch> <dir>: history and trees only, no checkout, index at HEAD
  GIT_LFS_SKIP_SMUDGE=1 git -c filter.lfs.process= -c filter.lfs.required=false clone -q --filter=blob:none \
    --no-checkout -b "$2" "https://x-access-token:${GH_TOKEN}@github.com/ford-op/$1.git" "$3"
  git -C "$3" read-tree HEAD
}
bump() {  # <dir> <path> <commit> <branch> <message>: commit a new gitlink and push it as <branch>, the
  # job's own branch (forced, so a rerun after a failure replaces its earlier attempt)
  git -C "$1" update-index --cacheinfo "160000,$3,$2"
  git -C "$1" -c filter.lfs.process= -c filter.lfs.required=false commit -q -m "$5"
  git -C "$1" push -q --force origin "HEAD:refs/heads/$4"
}
open_pr() {  # <repo> <base> <branch> <title> <body>: the branch's open PR, or a new one
  local url
  url=$(gh pr list -R "ford-op/$1" -H "$3" --state open --json url -q '.[0].url')
  if [ -n "$url" ]; then gh pr edit "$url" --title "$4" --body "$5" >/dev/null; echo "$url"
  else gh pr create -R "ford-op/$1" -B "$2" -H "$3" --title "$4" --body "$5"; fi
}
# bg-clean's required checks (its branch protection; the App can't read protection, so they're listed)
REQUIRED=("./test.sh (Linux)" "safety" "bluepilot-safety" "bluepilot-hooks")
wait_required() {  # <pr>: until every required check has reported and passed; fails on the first failure
  local out n state
  for _ in $(seq 150); do
    out=$(gh pr checks "$1" --required --json name,bucket 2>/dev/null || true)
    if jq -e 'any(.[]; .bucket == "fail" or .bucket == "cancel")' <<<"${out:-[]}" >/dev/null; then
      jq -r '.[] | select(.bucket == "fail" or .bucket == "cancel") | "failed: \(.name)"' <<<"$out"; return 1
    fi
    n=0
    for name in "${REQUIRED[@]}"; do
      state=$(jq -r --arg n "$name" '.[] | select(.name == $n) | .bucket' <<<"${out:-[]}")
      [ "$state" = pass ] && n=$((n + 1))
    done
    [ "$n" = "${#REQUIRED[@]}" ] && return 0
    sleep 20
  done
  echo "required checks didn't finish in 50 minutes"; return 1
}

# 1. bg-opendbc: the library pointer, merged on green
clone bg-opendbc bg-clean "$WORK/bg"
PIN=$(git -C "$WORK/bg" rev-parse HEAD:opendbc/bluepilot_lateral)
if ! git -C "$LIB" merge-base --is-ancestor "$PIN" "$SHA"; then
  echo "$TAG (${SHA:0:8}) isn't ahead of bg-opendbc's pin ${PIN:0:8}: nothing to do"; exit 1
fi
if [ "$PIN" = "$SHA" ]; then
  echo "bg-opendbc already pins $TAG"
  BG=$(git -C "$WORK/bg" rev-parse HEAD)
else
  BRANCH="bump/library-$TAG"
  bump "$WORK/bg" opendbc/bluepilot_lateral "$SHA" "$BRANCH" "bluepilot_lateral: bump to $TAG"
  PR=$(open_pr bg-opendbc bg-clean "$BRANCH" "bluepilot_lateral: bump to $TAG" \
"The library pointer moves to bluepilot-lateral [$TAG](https://github.com/BluePilotDev/bluepilot-lateral/releases/tag/$TAG) (${SHA:0:8}). Opened by the library's release job, which merges it once the required checks pass (ford-op/bg-opendbc#97).

## Validation
- [ ] CI \`./test.sh (Linux)\`
- [ ] CI \`safety\`
- [ ] CI \`bluepilot-safety\`
- [ ] CI \`bluepilot-hooks\`")
  echo "bg-opendbc: $PR"
  wait_required "$PR"
  gh pr view "$PR" --json body -q .body | sed 's/^- \[ \] CI/- [x] CI/' > "$WORK/body.md"
  gh pr edit "$PR" --body-file "$WORK/body.md"
  gh pr merge "$PR" --squash --delete-branch
  BG=$(gh pr view "$PR" --json mergeCommit -q .mergeCommit.oid)
  git -C "$WORK/bg" fetch -q origin bg-clean
fi

# 2. bp-sunnypilot: opendbc_repo to that bg-clean, as a PR
clone bp-sunnypilot master-local-lateral "$WORK/sp"
OLD=$(git -C "$WORK/sp" rev-parse HEAD:opendbc_repo)
if [ "$OLD" = "$BG" ]; then echo "bp-sunnypilot already at ${BG:0:8}"; exit 0; fi
OLDLIB=$(git -C "$WORK/bg" rev-parse "$OLD:opendbc/bluepilot_lateral")
changed() {  # what moved: bg-opendbc outside the library, then the library itself
  git -C "$WORK/bg" diff --name-only "$OLD" "$BG" -- . ':!opendbc/bluepilot_lateral'
  git -C "$LIB" diff --name-only "$OLDLIB" "$SHA" | sed 's|^|opendbc/bluepilot_lateral/|'
}
FILES=$(changed)
NOTESTS=$(grep -v '/tests/' <<<"$FILES" || true)
FW=$(grep -E '\.(h|c)$' <<<"$NOTESTS" || true)
LAT=$(grep -E '^opendbc/(bluepilot_lateral|car/ford|sunnypilot/car/ford)/.*\.py$|^opendbc/car/(lateral|interfaces|structs)\.py$|^opendbc/sunnypilot/car/interfaces\.py$|^opendbc/dbc/ford' <<<"$NOTESTS" || true)
# shellcheck disable=SC2016  # the backticks are Markdown, not expansions
list() { if [ -n "$1" ]; then sed 's/^/  - `/; s/$/`/' <<<"$1"; else echo "  - none"; fi; }
DRIVE=""
[ -n "$FW$LAT" ] && DRIVE="
- [ ] A drive (panda firmware or lateral Python changed)"
BRANCH="opendbc/library-$TAG"
bump "$WORK/sp" opendbc_repo "$BG" "$BRANCH" "opendbc_repo: bg-clean ${BG:0:8} (bluepilot-lateral $TAG)"
open_pr bp-sunnypilot master-local-lateral "$BRANCH" "opendbc_repo: bluepilot-lateral $TAG" \
"\`opendbc_repo\` moves to bg-opendbc \`bg-clean\` ${BG:0:8}, which has bluepilot-lateral [$TAG](https://github.com/BluePilotDev/bluepilot-lateral/releases/tag/$TAG). Opened by the library's release job (ford-op/bg-opendbc#97); not merged automatically.

- Panda firmware (\`.h\`/\`.c\`) changed:
$(list "$FW")
- Lateral Python or Ford DBC changed (outside tests):
$(list "$LAT")

## Validation
- [ ] CI \`build release\`
- [ ] CI \`build macOS\`
- [ ] CI \`static analysis\`
- [ ] CI \`unit tests\`
- [ ] CI \`process replay\`: only the known Ford segment differs (\`regen755D8CB1E1F\`, \`card\` \`sendcan\`)$DRIVE"
