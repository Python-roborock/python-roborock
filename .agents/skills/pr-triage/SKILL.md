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

2. **Query Open PR (& Optional Issue) Metadata**:
   Identify the current GitHub user and fetch open PR state in a single `gh` pass (`--limit 100` avoids truncating older PRs when the queue exceeds 30):
   ```bash
   REVIEWER=$(gh api user --jq .login)
   gh pr list --repo Python-roborock/python-roborock --state open --limit 100 \
     --json number,title,url,author,isDraft,createdAt,updatedAt,additions,deletions,mergeable,reviewDecision,headRefOid,statusCheckRollup,reviews,commits,comments \
     | jq --arg me "$REVIEWER" '
       sort_by(.number) | reverse | .[] | .author.login as $pr_author | {
         number,
         title,
         url,
         author: $pr_author,
         isDraft,
         mergeable,
         size: "+\(.additions)/-\(.deletions)",
         reviewDecision,
         headRefOid,
         ciState: (
           if (.statusCheckRollup | length) == 0 then "PENDING_APPROVAL_OR_NONE"
           elif ([.statusCheckRollup[] | select(.conclusion == "FAILURE" or .conclusion == "CANCELLED")] | length) > 0 then "FAILING"
           elif ([.statusCheckRollup[] | select(.status != "COMPLETED")] | length) > 0 then "RUNNING"
           else "PASSING" end
         ),
         lastCommit: (.commits | last | .committedDate),
         myLastReview: ([.reviews[] | select(.author.login == $me)] | last | {state, submittedAt, commitOid: .commit.oid}),
         otherLastReview: ([.reviews[] | select(.author.login != $me and .author.login != $pr_author and .author.login != "copilot-pull-request-reviewer")] | last | {author: .author.login, state, submittedAt}),
         lastAuthorReplyAt: (
           [
             (.comments[] | select(.author.login == $pr_author) | .createdAt),
             (.reviews[] | select(.author.login == $pr_author) | .submittedAt)
           ] | max
         )
       }'
   ```
   *(Note: GitHub's GraphQL `reviews` array includes `COMMENTED` entries whenever an author replies in an inline review thread, so combining `.comments[]` and `.reviews[]` filtered to `$pr_author` captures both top-level PR comments and inline review-thread replies without extra API calls.)*

   - **When Also Triaging Incoming Issues**: Fetch open issues in parallel and cross-reference open PRs that mention or close them:
     ```bash
     gh issue list --repo Python-roborock/python-roborock --state open --limit 50 \
       --json number,title,url,author,labels,createdAt,updatedAt,comments
     ```
     Group incoming issues into: (a) **Has Linked Open PR** (review the PR to close the issue), (b) **New / Unanswered Bug Reports & Hardware Captures** (actionable protocol/trait bugs with device payloads), and (c) **Feature Requests / Needs Info**.

3. **Classify PRs into Actionable Buckets**:
   Group open PRs in priority order for the reviewer (`$REVIEWER`):
   - **1. New PRs Awaiting Initial Review**:
     Non-draft PRs not authored by `$REVIEWER` where `myLastReview.submittedAt == null`. Flag competing/overlapping PRs targeting the same module/issue and note if another maintainer already commented/approved.
   - **2. Re-reviews Needed (Updated Since Last Review)**:
     Non-draft PRs not authored by `$REVIEWER` where `myLastReview.submittedAt != null` AND (`headRefOid != myLastReview.commitOid` OR `(lastAuthorReplyAt != null and lastAuthorReplyAt > myLastReview.submittedAt)`). Comparing `headRefOid != myLastReview.commitOid` catches amended, rebased, or cherry-picked commits whose `committedDate` precedes `myLastReview.submittedAt`.
   - **3. Approved & Ready to Merge / Own PR Updates**:
     - Non-draft PRs (authored by `$REVIEWER` or contributors) that are `APPROVED` (`reviewDecision == "APPROVED"`), `MERGEABLE`, and have no unreviewed commits since approval (`headRefOid == myLastReview.commitOid` or authored by `$REVIEWER`).
     - Non-draft PRs authored by `$REVIEWER` with new review feedback or merge conflicts requiring action.
   - **4. Waiting on Author / Drafts (Compact Summary)**:
     - Non-draft PRs with `CHANGES_REQUESTED` or `COMMENTED` where `headRefOid == myLastReview.commitOid` and no new author replies (`lastAuthorReplyAt <= myLastReview.submittedAt`) have arrived.
     - Draft PRs (`isDraft == true`), summarized compactly on 1–2 lines unless a draft has notable recent maintainer discussion.
     - Conflicting (`mergeable == "CONFLICTING"`) or stale backlog items.

4. **Present Concise Triage Report**:
   - Report sync status in one line if a sync was performed (commit hash + any new release tags).
   - **Always use clickable Markdown links** (`[#number](url)`) for every PR and issue mentioned.
   - List actionable PRs (`[#number](url)`, title, `@author`, `+additions/-deletions`, `ciState`, and why it needs attention—e.g., *opened Nov 14, closes [#1043](url)* or *updated Nov 9 after your Nov 8 review*).
   - Keep "Waiting on Author / Drafts" brief so actionable reviews stand out.
   - Conclude with a **Recommended Next Batch (3–5 non-overlapping PRs)** ordered from fast green-CI wins to high-impact bugfixes, noting any PRs awaiting first-time contributor CI approval.
