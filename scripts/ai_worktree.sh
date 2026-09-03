#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ai_worktree.sh setup [worktree-root]
  bash scripts/ai_worktree.sh status [worktree-root]
  bash scripts/ai_worktree.sh start <research|web-docs> <branch> [worktree-root]
  bash scripts/ai_worktree.sh finish <research|web-docs> [worktree-root]

Environment overrides:
  AI_WORKTREE_ROOT      Override the default sibling worktree directory.
  AI_WORKTREE_BASE_REF  Override the setup base ref (default: origin/main).
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_git_repo() {
  git rev-parse --git-dir >/dev/null 2>&1 || fail "run this from a crypto-autopilot Git checkout"
}

primary_root() {
  git worktree list --porcelain | awk '/^worktree / {print substr($0, 10); exit}'
}

resolve_root() {
  local explicit_root="${1:-}"
  local primary
  primary="$(primary_root)"
  if [[ -n "$explicit_root" ]]; then
    printf '%s\n' "$explicit_root"
  elif [[ -n "${AI_WORKTREE_ROOT:-}" ]]; then
    printf '%s\n' "$AI_WORKTREE_ROOT"
  else
    printf '%s/%s-worktrees\n' "$(dirname "$primary")" "$(basename "$primary")"
  fi
}

lane_path() {
  local root="$1"
  local lane="$2"
  case "$lane" in
    research|web-docs) printf '%s/%s\n' "$root" "$lane" ;;
    *) fail "unknown lane '$lane' (expected research or web-docs)" ;;
  esac
}

ensure_origin() {
  local primary="$1"
  git -C "$primary" remote get-url origin >/dev/null 2>&1 || fail "origin remote is missing"
}

fetch_main() {
  local primary="$1"
  ensure_origin "$primary"
  git -C "$primary" fetch --prune origin
  git -C "$primary" rev-parse --verify 'origin/main^{commit}' >/dev/null 2>&1 || fail "origin/main is unavailable"
}

worktree_registered() {
  local primary="$1"
  local path="$2"
  git -C "$primary" worktree list --porcelain \
    | awk '/^worktree / {print substr($0, 10)}' \
    | grep -Fxq "$path"
}

branch_checked_out() {
  local primary="$1"
  local branch="$2"
  git -C "$primary" worktree list --porcelain \
    | grep -Fxq "branch refs/heads/$branch"
}

validate_branch_name() {
  local branch="$1"
  [[ "$branch" != "main" && "$branch" != "master" ]] || fail "never use the main/master branch as an AI task branch"
  git check-ref-format --branch "$branch" >/dev/null 2>&1 || fail "invalid branch name '$branch'"
}

lane_is_clean() {
  local path="$1"
  [[ -z "$(git -C "$path" status --porcelain)" ]]
}

show_status() {
  local primary="$1"
  local root="$2"
  printf '\nPrimary + registered worktrees:\n'
  git -C "$primary" worktree list

  printf '\nAI lanes:\n'
  local lane path branch dirty counts behind ahead
  for lane in research web-docs; do
    path="$(lane_path "$root" "$lane")"
    if [[ ! -d "$path" ]] || ! worktree_registered "$primary" "$path"; then
      printf '  %-9s  NOT_SETUP  %s\n' "$lane" "$path"
      continue
    fi

    branch="$(git -C "$path" symbolic-ref --short -q HEAD || true)"
    [[ -n "$branch" ]] || branch="DETACHED"
    dirty="$(git -C "$path" status --porcelain | wc -l | tr -d ' ')"
    counts="$(git -C "$path" rev-list --left-right --count origin/main...HEAD 2>/dev/null || printf '0\t0')"
    behind="${counts%%[[:space:]]*}"
    ahead="${counts##*[[:space:]]}"
    printf '  %-9s  branch=%-36s changes=%s behind-main=%s ahead-main=%s\n' \
      "$lane" "$branch" "$dirty" "$behind" "$ahead"
  done
  printf '\n'
}

cmd_setup() {
  local root="$1"
  local primary base_ref lane path
  primary="$(primary_root)"
  base_ref="${AI_WORKTREE_BASE_REF:-origin/main}"

  ensure_origin "$primary"
  git -C "$primary" fetch --prune origin
  git -C "$primary" rev-parse --verify "$base_ref^{commit}" >/dev/null 2>&1 || fail "base ref '$base_ref' is unavailable"
  mkdir -p "$root"

  for lane in research web-docs; do
    path="$(lane_path "$root" "$lane")"
    if worktree_registered "$primary" "$path"; then
      printf '%s lane already exists: %s\n' "$lane" "$path"
      continue
    fi
    if [[ -e "$path" ]] && [[ -n "$(ls -A "$path" 2>/dev/null || true)" ]]; then
      fail "refusing to overwrite non-empty path: $path"
    fi
    git -C "$primary" worktree add --detach "$path" "$base_ref"
  done

  show_status "$primary" "$root"
  cat <<EOF
Worktree lanes are ready.

Start a new task with a unique branch, for example:
  bash scripts/ai_worktree.sh start research research/failed-breakout-v0-1 "$root"
  bash scripts/ai_worktree.sh start web-docs web/strategy-dashboard-v0-1 "$root"
EOF
}

cmd_start() {
  local root="$1"
  local lane="$2"
  local branch="$3"
  local primary path current
  primary="$(primary_root)"
  path="$(lane_path "$root" "$lane")"
  validate_branch_name "$branch"

  [[ -d "$path" ]] && worktree_registered "$primary" "$path" || fail "lane '$lane' is not set up; run setup first"
  lane_is_clean "$path" || fail "lane '$lane' has uncommitted changes; commit/stash/review them before switching tasks"

  current="$(git -C "$path" symbolic-ref --short -q HEAD || true)"
  if [[ -n "$current" ]]; then
    if [[ "$current" == "$branch" ]]; then
      printf "lane '%s' is already on %s\n" "$lane" "$branch"
      show_status "$primary" "$root"
      return
    fi
    fail "lane '$lane' is still attached to '$current'; finish that task before starting another"
  fi

  fetch_main "$primary"
  branch_checked_out "$primary" "$branch" && fail "branch '$branch' is already checked out in another worktree"

  git -C "$path" switch --detach origin/main
  if git -C "$primary" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$path" switch "$branch"
  elif git -C "$primary" show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    git -C "$path" switch --track -c "$branch" "origin/$branch"
  else
    git -C "$path" switch -c "$branch" origin/main
  fi

  printf "Started %s task on branch %s at %s\n" "$lane" "$branch" "$path"
  show_status "$primary" "$root"
}

cmd_finish() {
  local root="$1"
  local lane="$2"
  local primary path branch
  primary="$(primary_root)"
  path="$(lane_path "$root" "$lane")"

  [[ -d "$path" ]] && worktree_registered "$primary" "$path" || fail "lane '$lane' is not set up"
  lane_is_clean "$path" || fail "lane '$lane' has uncommitted changes; refusing to detach or delete anything"

  branch="$(git -C "$path" symbolic-ref --short -q HEAD || true)"
  fetch_main "$primary"

  if [[ -z "$branch" ]]; then
    git -C "$path" switch --detach origin/main
    printf "lane '%s' is already free and refreshed to origin/main\n" "$lane"
    show_status "$primary" "$root"
    return
  fi

  if ! git -C "$primary" merge-base --is-ancestor "$branch" origin/main; then
    fail "branch '$branch' is not merged into origin/main; keep the lane intact, push/open/merge its PR first"
  fi

  git -C "$path" switch --detach origin/main
  git -C "$primary" branch -d "$branch"
  printf "Finished %s task; lane is clean, detached, and refreshed to origin/main\n" "$lane"
  show_status "$primary" "$root"
}

main() {
  require_git_repo
  local command="${1:-}"
  shift || true

  case "$command" in
    setup)
      cmd_setup "$(resolve_root "${1:-}")"
      ;;
    status)
      show_status "$(primary_root)" "$(resolve_root "${1:-}")"
      ;;
    start)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      local lane="$1" branch="$2" explicit_root="${3:-}"
      cmd_start "$(resolve_root "$explicit_root")" "$lane" "$branch"
      ;;
    finish)
      [[ $# -ge 1 ]] || { usage; exit 2; }
      local lane="$1" explicit_root="${2:-}"
      cmd_finish "$(resolve_root "$explicit_root")" "$lane"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage
      fail "unknown command '$command'"
      ;;
  esac
}

main "$@"
