---
name: c4flow:sync
description: Sync local project with remote sources — pulls DoltHub beads and GitHub repo to local. Handles the "no common ancestor" Dolt error that occurs when bd init creates a fresh local DB that conflicts with an existing DoltHub history. Use when local beads are out of sync, after a fresh init on a project that already has DoltHub data, or to pull the latest GitHub changes.
---

# /c4flow:sync — Remote Sync (DoltHub + GitHub)

**Agent type**: Main agent (interactive)

## What It Does

Syncs both Dolt beads and GitHub code to the local workspace:

1. **Dolt sync** — runs `scripts/dolt_sync.sh` which handles all cases automatically
2. **GitHub sync** — `git pull` from origin

## Step 1: Dolt Sync via Script

Find the skill's `scripts/dolt_sync.sh` (in the same directory as this SKILL.md), then run it from the project root:

```bash
bash <skill-dir>/scripts/dolt_sync.sh "$(pwd)"
```

The script handles all cases automatically:
- Reads `doltRemote` from `.state.json`
- Creates inner DB if missing (`MISSING_DB`)
- Adds remote if not configured (`NEEDS_REMOTE`)
- Starts server, fetches, resets if no common ancestor, restarts server
- Reports HEAD and bead count

If the script exits with an error, report it to the user verbatim — don't try to fix it manually, as improvised bash can corrupt the Dolt journal.

**Critical rule the script enforces**: `dolt reset --hard` only runs while the server is live. Doing it while the server is stopped corrupts journal files and breaks the server.

## Step 2: GitHub Sync

```bash
git status --short 2>&1
git remote -v 2>&1 | head -2
```

If there are uncommitted changes, ask the user: stash and pull, commit first, or skip?

If clean:
```bash
git pull origin $(git rev-parse --abbrev-ref HEAD) 2>&1
```

| Error | Action |
|-------|--------|
| `no tracking information` | `git branch --set-upstream-to=origin/main main` then retry |
| `merge conflict` | Show conflicting files, tell user to resolve manually |
| `not a git repository` | Skip GitHub sync, note it |

## Step 3: Report

```
✅ Dolt sync complete
   Remote: <url>
   HEAD: <hash> (<message>)
   Beads: <N> issues

✅ GitHub sync complete
   Branch: <branch>
   Status: <result>
```

## Error Reference

| Error from script | Cause | Fix |
|-------------------|-------|-----|
| `No .state.json found` | Missing state file | Run `c4flow:init` |
| `No doltRemote in .state.json` | DoltHub not configured | Run `c4flow:init --remote <url>` |
| `DoltHub authentication required` | Not logged in | `dolt login` |
| `Local DB has N commits` | May have local-only data | Review manually before reset |
| `Server failed to restart` | Journal issue | Check `bd dolt status` and logs |
