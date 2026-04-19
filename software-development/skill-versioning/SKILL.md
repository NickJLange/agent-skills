---
name: skill-versioning
description: Nightly git versioning for skills and private state, with GitHub PR workflow and CI testing.
version: 0.2.0
author: Hermes Agent
metadata:
  hermes:
    tags: [skills, versioning, git, github, ci]
status: implemented
---

# Skill Versioning — Implementation

## Overview

Two git repos for tracking Hermes agent evolution:
1. **agent-skills** (public) — shareable skills, compared against upstream
2. **agent-memories** (private) — memory exports, user profile, config

## Repos

### Skills Repo
- GitHub: `5L-hermes01/agent-skills` (public)
- Local: `/opt/data/skills/`
- Upstream source: `NousResearch/hermes-agent` (skills/ dir)
- Only commits local modifications and new skills — never re-pushes inherited upstream content

### Private Repo
- GitHub: `5L-hermes01/agent-memories` (private)
- Local: `/opt/data/repos/agent-memories/`
- Commits everything (no upstream to compare against)

## Nightly Flow

Script: `/opt/data/scripts/nightly-repo-sync.py`
Cron: `nightly-repo-sync` at 03:00 UTC daily

### agent-memories (direct commit)
1. `git add -A`
2. If changes: branch `update/YYYY-MM-DD`, commit, push, open PR
3. Auto-merge via GitHub Actions when smoke tests pass

### agent-skills (upstream-aware)
1. Fetch upstream to read-only clone at `/opt/data/upstream-hermes-agent`
2. Build file map of upstream's `skills/` directory
3. Compare each local file against upstream by content hash
4. Classify files as:
   - **New**: exists locally, not in upstream (our custom skills)
   - **Modified**: exists in both, content differs
5. Stage only new + modified files (skip gitignored)
6. Branch, commit, push, open PR
7. Auto-merge when smoke tests pass

### Both repos
- Diff report delivered to user in chat for review
- GitHub Actions: smoke-tests.yml + auto-merge.yml

## Key Implementation Details

### Upstream Comparison Pattern
- **Never add upstream as a git remote** in the working repo — risk of accidental push
- Clone upstream to a separate read-only path instead
- Compare by file content (bytes), not git tree hashes — handles path mapping differences
- Our repo has skills at root (`/opt/data/skills/social-media/xitter/`)
- Upstream has them under `skills/` (`skills/social-media/xitter/`)

### Gitignore Handling
- Before staging each file, run `git check-ignore -q <file>`
- Skip if exit code is 0 (ignored)
- Prevents errors on files like `.bundled_manifest`

### Auto-merge Without Branch Protection
- Branch protection requires GitHub Pro for private repos
- Workaround: use `workflow_run` trigger on "Smoke Tests" completion
- Auto-merge workflow fires only when smoke tests conclude with `success`
- Effectively the same as required checks, no Pro needed

## GitHub Actions Workflows

### smoke-tests.yml
- Runs on PR and push to main
- Checks: leaked secrets (regex), SKILL.md frontmatter (name, description), file encoding, referenced directories

### auto-merge.yml
- Trigger: `workflow_run` on "Smoke Tests" completion
- If success: finds PR by head SHA, runs `gh pr merge --squash --delete-branch`
- If failure: does nothing (PR stays open for manual review)

## Cron Job
- Name: `nightly-repo-sync`
- Schedule: `0 3 * * *` (03:00 UTC)
- Script: `/opt/data/scripts/nightly-repo-sync.py`
- Delivery: results sent to user's chat for review

## Pitfalls
- SSH key for agent-skills needs explicit config: `git config core.sshCommand "ssh -i /opt/data/config/github/hermes-agent -o StrictHostKeyChecking=accept-new"`
- agent-memories uses HTTPS with PAT embedded in remote URL (different auth method)
- Upstream clone must use HTTPS (bot's SSH key doesn't have access to NousResearch repos)
- Force push needed on first push if GitHub auto-created initial commit
- `git add -A` can pick up gitignored files if .gitignore was just created — always check-ignore first
