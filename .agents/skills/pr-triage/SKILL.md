---
name: pr-triage
description: >-
  Assess open pull requests, incoming issues, and review queue state in python-roborock, optionally syncing the local workspace with upstream/main. Use when asked what needs to be reviewed, to triage open PRs or incoming issues, or to sync and check the review backlog.
---

# PR & Issue Triage Skill

Use this skill when assessing open pull requests, triaging incoming issues, checking which PRs need initial review or re-review, or syncing the workspace before starting a review session.

Once the user selects a specific PR to review, switch to the [Code Review Skill](../code-review/SKILL.md).

---

## Workflow

1. **Workspace Fetch & Optional Sync**:
   Always `git fetch upstream main` so local context reflects current `upstream/main`. If the user asks to sync (e.g., "sync and check reviews") or the workspace is a clean review branch behind `upstream/main`:
   - Verify clean working tree (`git status --short`). Do **not** fast-forward or rebase if uncommitted local changes exist unless asked.
   - Fetch remotes (`git fetch --all --prune`).
   - Fast-forward the local tracking branch to `upstream/main` (or `origin/main` if `upstream` is absent): `git merge --ff-only upstream/main`.

2. **Run the Single-Pass Triage Script**:
   Execute [`scripts/triage.py`](scripts/triage.py) with `prs`, `issues`, or `all` depending on what the user asked to triage. Each subcommand runs a single GraphQL call (up to 100 open PRs / 50 open issues) without hitting `gh pr list` node-count limits:
   ```bash
   # Triage open PRs only (review buckets + suggested 5-PR batch)
   python3 .agents/skills/pr-triage/scripts/triage.py prs

   # Triage incoming open issues only (still cross-linking open PRs without dumping the PR queue)
   python3 .agents/skills/pr-triage/scripts/triage.py issues

   # Triage both open PRs and open issues in a single pass
   python3 .agents/skills/pr-triage/scripts/triage.py all
   ```
   *(Pass `--json` if structured output is needed for custom filtering.)*

3. **Verify Actionable Buckets**:
   The script classifies open PRs for the authenticated reviewer into four priority buckets:
   - **1. New PRs Awaiting Initial Review**: Non-draft contributor PRs you have not yet reviewed, annotated with file overlaps (`overlaps #...`), referenced issues, CI state (`SUCCESS`, `FAILURE`, `PENDING_APPROVAL`), and other maintainer reviews.
   - **2. Re-reviews Needed**: Non-draft PRs where `headRefOid != myLastReview.commitOid` (catches amended/rebased commits) or the author replied after `myLastReview.submittedAt`.
   - **3. Ready to Merge / Own PRs**: Approved, mergeable PRs with no unreviewed commits, plus your own open PRs (highlighting merge conflicts or unresolved Copilot/review threads).
   - **4. Waiting on Author & Drafts**: Compact summary of PRs awaiting contributor changes and draft PRs.

4. **Present Concise Triage Report**:
   - Report sync status in one line if a sync was performed (commit hash + any new release tags).
   - **Always preserve clickable Markdown links** (`[#number](url)`) for every PR and issue mentioned.
   - Highlight high-signal relationships (e.g., competing PRs touching the same module, stacked PR series from the same author, or issues already addressed by an open PR).
   - Conclude with the **Suggested Next Review Batch (3–5 non-overlapping PRs)** ordered from quick green-CI wins to high-impact bugfixes, noting any PRs awaiting first-time contributor CI approval.
