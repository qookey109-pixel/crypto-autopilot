# AI Worktree Workflow V0.1

Status: **DEVELOPER WORKFLOW ONLY / NO EXECUTION AUTHORITY**

This workflow isolates parallel AI-assisted development without changing any
provider, R2, holdout, model-promotion or trading authority. Repository `main`
remains the formal source of truth.

## Why this exists

A Git branch isolates history, but one ordinary checkout can show only one
branch at a time. `git worktree` adds additional local checkout directories
that share the same Git object database. This lets separate AI tools or agent
sessions work on separate tasks without constantly switching the same folder.

Worktrees do **not** increase Codex or other model usage limits. They reduce
collisions and repeated setup, and they make it practical to split work across
different AI tools while keeping one clean Repository authority.

## Default layout

After setup, the recommended local layout is:

```text
crypto-autopilot/                     primary checkout; keep main clean
crypto-autopilot-worktrees/
├── research/                         research / strategy task lane
└── web-docs/                         website / docs task lane
```

The two AI lanes are created in detached-HEAD state at `origin/main`. A lane
gets a task-specific branch only when work starts.

## One-time setup

From any existing `crypto-autopilot` Git checkout:

```bash
bash scripts/ai_worktree.sh setup
```

Check the current lanes at any time:

```bash
bash scripts/ai_worktree.sh status
```

The helper fetches `origin`, creates only sibling worktree directories, refuses
to overwrite a non-empty directory, and does not edit `main`.

## Start a task

Research example:

```bash
bash scripts/ai_worktree.sh start research research/failed-breakout-v0-1
```

Website/docs example:

```bash
bash scripts/ai_worktree.sh start web-docs web/strategy-dashboard-v0-1
```

The helper always refreshes `origin/main` first. If the requested branch exists
only on GitHub, it creates a local tracking branch. This is useful when an
online coding agent has already pushed a branch and you want to inspect or
continue it locally in an isolated lane.

Give the AI tool the corresponding directory, not the primary `main` checkout:

```text
.../crypto-autopilot-worktrees/research
.../crypto-autopilot-worktrees/web-docs
```

Each lane should contain exactly one active task branch at a time.

## Normal task lifecycle

```text
latest origin/main
      ↓
detached worktree lane
      ↓
task-specific branch
      ↓
AI edits + tests
      ↓
commit
      ↓
push branch
      ↓
PR + CI + review
      ↓
merge to main
      ↓
finish lane
```

After the PR is merged and the lane has no uncommitted changes:

```bash
bash scripts/ai_worktree.sh finish research
```

or:

```bash
bash scripts/ai_worktree.sh finish web-docs
```

`finish` fails closed unless the task branch is already contained in
`origin/main`. When safe, it detaches the lane back to the latest `origin/main`
and removes only the merged local task branch.

## Safety rules

1. Keep the primary `main` worktree clean. New feature/research/docs work starts
   in a task branch, not directly on `main`.
2. Always create a separate task branch for each independent AI task.
3. Never let two worktrees check out the same local branch.
4. Do not use `git reset --hard`, `git clean -fd`, force-push, worktree removal,
   or branch deletion as an automatic conflict fix when uncommitted work exists.
5. Before resolving a conflict, identify which product/authority behavior must
   win. Do not ask an AI to blindly choose "ours" or "theirs".
6. `.gitignore`, secret handling and all rules in `AGENTS.md` apply identically
   in every worktree.
7. A worktree or branch grants **zero** provider/R2/holdout/model/trading
   authority. Versioned Repository authority still controls execution.
8. After a GitHub PR merge, local worktrees do not update automatically. Use the
   helper's `finish`/`start` flow or explicitly fetch before new work.

## If the primary repository is not cloned yet

A ZIP download is not sufficient for this workflow. Clone once, then run setup:

```bash
cd ~/Desktop
git clone https://github.com/qookey109-pixel/crypto-autopilot.git
cd crypto-autopilot
bash scripts/ai_worktree.sh setup
```

If a clone already exists elsewhere, use that existing clone instead of making
a duplicate.

## Working with online AI branches

Online Codex or another GitHub-connected agent does not directly use the local
Mac worktree directories. It works through GitHub branches. The safe bridge is:

1. let the online agent create/push one task branch;
2. locally run `git fetch origin` (the helper does this automatically);
3. attach that remote branch to the matching worktree lane with `start`;
4. inspect/test/continue locally without touching the primary `main` folder;
5. merge through PR/CI, then `finish` the lane.

This separates cloud-agent work, local-agent work and the formal `main`
authority while preserving one shared Git history.
