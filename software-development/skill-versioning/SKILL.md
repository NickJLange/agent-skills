---
name: skill-versioning
description: Nightly git versioning for skills and private state, with GitHub PR workflow and CI testing.
version: 0.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [skills, versioning, git, github, ci]
status: design-phase
---

# Skill Versioning — Design Doc

## Overview

Two git repos for tracking Hermes agent evolution:
1. **Skills repo** (shareable) — for team collaboration
2. **Private repo** (private) — memory, state, config

## Repos

### Skills Repo
- Location: `/opt/data/skills/`
- GitHub: TBD (need user + repo access setup)
- Contents: SKILL.md files, references/, templates/, scripts/
- Shareable between team members
- Other agents clone/pull for shared skills

### Private Repo
- Location: `/opt/data/state/`
- GitHub: TBD (private repo)
- Contents: Memory exports, user profile, config, content state
- Never shared

## Nightly Flow

### Skills Repo (GitHub PR workflow)
1. Create branch `update/YYYY-MM-DD`
2. `git add` all skill files
3. Commit with summary of changes
4. Push branch to GitHub
5. Open PR with diff summary against main
6. GitHub Actions runs test suite
7. Auto-merge when CI passes (or wait for review)
8. Local pull after merge

### Private Repo (direct push)
1. Export memory to markdown
2. Export user profile to markdown
3. Commit + push directly to main
4. No PR — just state snapshots

## Diff Reports (sent to user)

### Skills repo format:
- "Added: new skill X"
- "Modified: x-digest (3 sections changed)"
- "Removed: old-skill-name"
- Inline diff for small changes, summary for large

### Private repo format:
- "Memory: added entry about X, removed entry about Y"
- "User profile: no changes"
- "Content state: 5 new YT transcripts"

## GitHub Actions Test Suite

Tests to run on every skill PR:
- [ ] SKILL.md has required frontmatter (name, description, version)
- [ ] No secrets/tokens in skill files
- [ ] All referenced files in references/ exist
- [ ] Markdown renders without errors
- [ ] Code blocks have valid syntax (Python, bash)
- [ ] No broken internal links
- [ ] Skill doesn't exceed size limits
- [ ] Custom per-skill tests (skill-specific scripts)

## Setup Checklist

- [ ] Create GitHub user/bot account for Hermes
- [ ] Create skills repo (public or org-visible)
- [ ] Create private repo (private)
- [ ] Set up SSH keys or PAT for push access
- [ ] Initialize local git repos
- [ ] Write export-memory-to-markdown script
- [ ] Write nightly commit/PR script
- [ ] Create GitHub Actions workflow for skill tests
- [ ] Create cron job for nightly run
- [ ] Configure auto-merge rules (squash on green?)
- [ ] Set up .gitignore (secrets, cache, media, venvs)

## Cron Jobs Needed

- `skill-versioning-nightly` — runs the commit/PR flow
- `skill-versioning-pull` — pulls merged changes back down (or add to nightly)

## Design Decisions

- Auto-merge on green vs always wait for review: TBD
- GitHub org: TBD (5L Labs?)
- Delivery of diff report: Signal or Discord: TBD
