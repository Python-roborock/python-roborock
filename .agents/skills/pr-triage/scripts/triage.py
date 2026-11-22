#!/usr/bin/env python3
"""Fetch and classify open PRs and/or open issues for python-roborock triage."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any

DEFAULT_REPO = "Python-roborock/python-roborock"
ISSUE_REF_RE = re.compile(r"(?:^|[\s(])#(\d+)\b")

GRAPHQL_QUERY = """
query(
  $owner: String!
  $name: String!
  $prLimit: Int!
  $includePrDetails: Boolean!
  $includeIssues: Boolean!
  $issueLimit: Int!
) {
  viewer {
    login
  }
  repository(owner: $owner, name: $name) {
    pullRequests(first: $prLimit, states: OPEN, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
        title
        url
        body
        isDraft
        closingIssuesReferences(first: 10) {
          nodes {
            number
          }
        }
        mergeable @include(if: $includePrDetails)
        reviewDecision @include(if: $includePrDetails)
        createdAt @include(if: $includePrDetails)
        updatedAt @include(if: $includePrDetails)
        additions @include(if: $includePrDetails)
        deletions @include(if: $includePrDetails)
        headRefOid @include(if: $includePrDetails)
        author @include(if: $includePrDetails) {
          login
        }
        files(first: 30) @include(if: $includePrDetails) {
          nodes {
            path
          }
        }
        reviewThreads(first: 50) @include(if: $includePrDetails) {
          nodes {
            isResolved
          }
        }
        commits(last: 1) @include(if: $includePrDetails) {
          nodes {
            commit {
              committedDate
              statusCheckRollup {
                state
              }
            }
          }
        }
        reviews(last: 40) @include(if: $includePrDetails) {
          nodes {
            state
            submittedAt
            author {
              login
            }
            commit {
              oid
            }
          }
        }
        comments(last: 30) @include(if: $includePrDetails) {
          nodes {
            createdAt
            author {
              login
            }
          }
        }
      }
    }
    issues(
      first: $issueLimit
      states: OPEN
      orderBy: {field: CREATED_AT, direction: DESC}
    ) @include(if: $includeIssues) {
      nodes {
        number
        title
        url
        createdAt
        updatedAt
        author {
          login
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
        comments {
          totalCount
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class ReviewSummary:
    """Summary of the latest review from a reviewer."""

    author: str
    state: str
    submitted_at: str
    commit_oid: str | None


@dataclass
class PullRequestItem:
    """Normalized pull request metadata for triage classification."""

    number: int
    title: str
    url: str
    author: str
    is_draft: bool
    mergeable: str
    review_decision: str | None
    created_at: str
    updated_at: str
    last_commit_at: str | None
    size: str
    additions: int
    deletions: int
    head_oid: str
    ci_state: str
    unresolved_threads: int
    files: list[str]
    linked_issues: list[int]
    overlapping_prs: list[int]
    my_last_review: ReviewSummary | None
    other_last_review: ReviewSummary | None
    last_author_reply_at: str | None
    reason: str = ""


@dataclass(frozen=True)
class IssueItem:
    """Normalized open issue metadata for triage."""

    number: int
    title: str
    url: str
    author: str
    created_at: str
    labels: list[str]
    comment_count: int
    linked_prs: list[int]


def _login(node: dict[str, Any] | None) -> str:
    if not node:
        return "ghost"
    author = node.get("author")
    if isinstance(author, dict) and isinstance(author.get("login"), str):
        return author["login"]
    return "ghost"


def _extract_issue_refs(pr_node: dict[str, Any], pr_numbers: set[int]) -> list[int]:
    refs: set[int] = set()
    closing = pr_node.get("closingIssuesReferences", {}).get("nodes") or []
    for item in closing:
        if isinstance(item, dict) and isinstance(item.get("number"), int):
            refs.add(item["number"])
    for text in (pr_node.get("title") or "", pr_node.get("body") or ""):
        for match in ISSUE_REF_RE.finditer(text):
            num = int(match.group(1))
            if num not in pr_numbers:
                refs.add(num)
    return sorted(refs)


def _parse_pr(node: dict[str, Any], reviewer: str, pr_numbers: set[int]) -> PullRequestItem:
    author = _login(node)
    commits = node.get("commits", {}).get("nodes") or []
    last_commit = commits[-1].get("commit", {}) if commits else {}
    rollup = last_commit.get("statusCheckRollup")
    ci_state = rollup.get("state", "UNKNOWN") if isinstance(rollup, dict) else "PENDING_APPROVAL"

    reviews_raw = [
        r for r in (node.get("reviews", {}).get("nodes") or []) if isinstance(r, dict) and r.get("state") != "PENDING"
    ]
    my_reviews = [r for r in reviews_raw if _login(r) == reviewer]
    other_reviews = [
        r for r in reviews_raw if _login(r) not in {reviewer, author, "copilot-pull-request-reviewer", "github-actions"}
    ]

    my_last: ReviewSummary | None = None
    if my_reviews:
        last_r = my_reviews[-1]
        commit_obj = last_r.get("commit")
        my_last = ReviewSummary(
            author=reviewer,
            state=last_r.get("state") or "",
            submitted_at=last_r.get("submittedAt") or "",
            commit_oid=commit_obj.get("oid") if isinstance(commit_obj, dict) else None,
        )

    other_last: ReviewSummary | None = None
    if other_reviews:
        last_o = other_reviews[-1]
        commit_obj = last_o.get("commit")
        other_last = ReviewSummary(
            author=_login(last_o),
            state=last_o.get("state") or "",
            submitted_at=last_o.get("submittedAt") or "",
            commit_oid=commit_obj.get("oid") if isinstance(commit_obj, dict) else None,
        )

    comments_raw = [c for c in (node.get("comments", {}).get("nodes") or []) if isinstance(c, dict)]
    author_timestamps = [
        ts
        for ts in (
            [c.get("createdAt") for c in comments_raw if _login(c) == author]
            + [r.get("submittedAt") for r in reviews_raw if _login(r) == author]
        )
        if isinstance(ts, str)
    ]
    last_author_reply = max(author_timestamps) if author_timestamps else None

    threads = [t for t in (node.get("reviewThreads", {}).get("nodes") or []) if isinstance(t, dict)]
    unresolved = sum(1 for t in threads if not t.get("isResolved", False))
    files = [
        f["path"]
        for f in (node.get("files", {}).get("nodes") or [])
        if isinstance(f, dict) and isinstance(f.get("path"), str)
    ]
    additions = int(node.get("additions") or 0)
    deletions = int(node.get("deletions") or 0)

    return PullRequestItem(
        number=int(node["number"]),
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        author=author,
        is_draft=bool(node.get("isDraft")),
        mergeable=str(node.get("mergeable") or "UNKNOWN"),
        review_decision=node.get("reviewDecision"),
        created_at=str(node.get("createdAt") or ""),
        updated_at=str(node.get("updatedAt") or ""),
        last_commit_at=last_commit.get("committedDate"),
        size=f"+{additions}/-{deletions}",
        additions=additions,
        deletions=deletions,
        head_oid=str(node.get("headRefOid") or ""),
        ci_state=ci_state,
        unresolved_threads=unresolved,
        files=files,
        linked_issues=_extract_issue_refs(node, pr_numbers),
        overlapping_prs=[],
        my_last_review=my_last,
        other_last_review=other_last,
        last_author_reply_at=last_author_reply,
    )


def _populate_overlaps(prs: list[PullRequestItem]) -> None:
    active = [p for p in prs if not p.is_draft]
    file_sets = {p.number: set(p.files) for p in active}
    for pr in active:
        my_files = file_sets[pr.number]
        if not my_files:
            continue
        pr.overlapping_prs = sorted(
            other.number for other in active if other.number != pr.number and (my_files & file_sets[other.number])
        )


def classify_prs(prs: list[PullRequestItem], reviewer: str) -> dict[str, list[PullRequestItem]]:
    """Classify open PRs into the four maintainer triage buckets."""
    buckets: dict[str, list[PullRequestItem]] = {
        "new_reviews": [],
        "re_reviews": [],
        "ready_or_own": [],
        "waiting_or_draft": [],
    }
    for pr in sorted(prs, key=lambda p: p.number, reverse=True):
        if pr.is_draft:
            pr.reason = "draft"
            buckets["waiting_or_draft"].append(pr)
            continue

        if pr.author == reviewer:
            notes = [f"own PR ({pr.mergeable}, CI: {pr.ci_state})"]
            if pr.review_decision:
                notes.append(pr.review_decision)
            if pr.unresolved_threads:
                notes.append(f"{pr.unresolved_threads} unresolved thread(s)")
            pr.reason = ", ".join(notes)
            buckets["ready_or_own"].append(pr)
            continue

        my_rev = pr.my_last_review
        if (
            pr.review_decision == "APPROVED"
            and pr.mergeable == "MERGEABLE"
            and (my_rev is None or my_rev.commit_oid == pr.head_oid)
        ):
            pr.reason = f"approved & mergeable (CI: {pr.ci_state})"
            buckets["ready_or_own"].append(pr)
            continue

        if my_rev is None:
            notes = [f"opened {pr.created_at[:10]}"]
            if pr.other_last_review:
                notes.append(f"@{pr.other_last_review.author}: {pr.other_last_review.state}")
            pr.reason = "; ".join(notes)
            buckets["new_reviews"].append(pr)
            continue

        has_new_commits = my_rev.commit_oid != pr.head_oid
        has_author_reply = pr.last_author_reply_at is not None and pr.last_author_reply_at > my_rev.submitted_at
        if has_new_commits or has_author_reply:
            triggers: list[str] = []
            if has_new_commits:
                triggers.append("new commits")
            if has_author_reply and pr.last_author_reply_at:
                triggers.append(f"author reply {pr.last_author_reply_at[:10]}")
            pr.reason = f"{' + '.join(triggers)} since {my_rev.state} ({my_rev.submitted_at[:10]})"
            buckets["re_reviews"].append(pr)
        else:
            pr.reason = f"waiting on author after {my_rev.state} ({my_rev.submitted_at[:10]})"
            buckets["waiting_or_draft"].append(pr)

    return buckets


def recommend_batch(buckets: dict[str, list[PullRequestItem]], max_count: int = 5) -> list[PullRequestItem]:
    """Select up to max_count non-overlapping actionable PRs ordered by quick wins."""
    candidates = [
        p
        for p in (buckets["re_reviews"] + buckets["new_reviews"])
        if p.mergeable != "CONFLICTING" and p.ci_state not in {"FAILURE", "ERROR"}
    ]
    candidates.sort(
        key=lambda p: (
            0 if p in buckets["re_reviews"] else 1,
            0 if p.ci_state == "SUCCESS" else 1,
            p.additions + p.deletions,
            -p.number,
        )
    )
    chosen: list[PullRequestItem] = []
    claimed_files: set[str] = set()
    for pr in candidates:
        pr_files = set(pr.files)
        if pr_files & claimed_files:
            continue
        chosen.append(pr)
        claimed_files |= pr_files
        if len(chosen) >= max_count:
            break
    return chosen


def _format_pr_line(pr: PullRequestItem) -> str:
    extras = [f"CI: `{pr.ci_state}`"]
    if pr.mergeable == "CONFLICTING":
        extras.append("`CONFLICTING`")
    if pr.unresolved_threads:
        extras.append(f"{pr.unresolved_threads} unresolved")
    if pr.linked_issues:
        refs = ", ".join(f"#{n}" for n in pr.linked_issues[:3])
        extras.append(f"refs {refs}")
    if pr.overlapping_prs:
        overlaps = ", ".join(f"#{n}" for n in pr.overlapping_prs[:3])
        suffix = f" +{len(pr.overlapping_prs) - 3}" if len(pr.overlapping_prs) > 3 else ""
        extras.append(f"overlaps {overlaps}{suffix}")
    meta = " | ".join(extras)
    return f"- [#{pr.number}]({pr.url}) — `{pr.title}` (`@{pr.author}`, `{pr.size}`, {meta}) — {pr.reason}"


def _render_prs_markdown(
    reviewer: str,
    prs: list[PullRequestItem],
    buckets: dict[str, list[PullRequestItem]],
) -> list[str]:
    lines = [f"## PR Triage Queue (`@{reviewer}` — {len(prs)} open PRs)", ""]

    sections = [
        ("1. New PRs Awaiting Initial Review", buckets["new_reviews"]),
        ("2. Re-reviews Needed (Updated Since Your Last Review)", buckets["re_reviews"]),
        ("3. Ready to Merge / Own PRs", buckets["ready_or_own"]),
    ]
    for heading, items in sections:
        lines.append(f"### {heading} ({len(items)})")
        if items:
            lines.extend(_format_pr_line(pr) for pr in items)
        else:
            lines.append("- None")
        lines.append("")

    waiting = [p for p in buckets["waiting_or_draft"] if not p.is_draft]
    drafts = [p for p in buckets["waiting_or_draft"] if p.is_draft]
    lines.append(f"### 4. Waiting on Author ({len(waiting)}) & Drafts ({len(drafts)})")
    if waiting:
        waiting_summary = ", ".join(
            f"[#{p.number}]({p.url}) (`@{p.author}`{', CONFLICTING' if p.mergeable == 'CONFLICTING' else ''})"
            for p in waiting
        )
        lines.append(f"- **Waiting on author**: {waiting_summary}")
    if drafts:
        draft_summary = ", ".join(f"[#{p.number}]({p.url}) (`@{p.author}`)" for p in drafts)
        lines.append(f"- **Drafts**: {draft_summary}")
    if not waiting and not drafts:
        lines.append("- None")
    lines.append("")

    batch = recommend_batch(buckets)
    if batch:
        lines.append(f"## Suggested Next Review Batch ({len(batch)} non-overlapping PRs)")
        for idx, pr in enumerate(batch, 1):
            lines.append(
                f"{idx}. [#{pr.number}]({pr.url}) — `{pr.title}` "
                f"(`@{pr.author}`, `{pr.size}`, CI: `{pr.ci_state}`) — {pr.reason}"
            )
        lines.append("")

    return lines


def _render_issues_markdown(repo: str, issues: list[IssueItem]) -> list[str]:
    with_pr = [i for i in issues if i.linked_prs]
    unlinked = [i for i in issues if not i.linked_prs]
    lines = [f"## Open Issues ({len(issues)} fetched)", ""]
    lines.append(f"### Linked to Open PRs ({len(with_pr)})")
    for issue in with_pr:
        pr_links = ", ".join(f"[#{n}](https://github.com/{repo}/pull/{n})" for n in issue.linked_prs)
        lines.append(f"- [#{issue.number}]({issue.url}) — `{issue.title}` (`@{issue.author}`) → PR {pr_links}")
    if not with_pr:
        lines.append("- None")
    lines.append("")
    lines.append(f"### Unlinked Open Issues ({len(unlinked)})")
    for issue in unlinked:
        lbls = f" [{', '.join(issue.labels)}]" if issue.labels else ""
        lines.append(
            f"- [#{issue.number}]({issue.url}) — `{issue.title}` (`@{issue.author}`, "
            f"opened {issue.created_at[:10]}, {issue.comment_count} comments){lbls}"
        )
    if not unlinked:
        lines.append("- None")
    lines.append("")
    return lines


def fetch_github_data(
    repo: str,
    pr_limit: int,
    include_pr_details: bool,
    include_issues: bool,
    issue_limit: int,
) -> dict[str, Any]:
    """Run a single GitHub GraphQL query via the gh CLI."""
    owner, name = repo.split("/", 1)
    cmd = [
        "gh",
        "api",
        "graphql",
        "-F",
        f"owner={owner}",
        "-F",
        f"name={name}",
        "-F",
        f"prLimit={pr_limit}",
        "-F",
        f"includePrDetails={'true' if include_pr_details else 'false'}",
        "-F",
        f"includeIssues={'true' if include_issues else 'false'}",
        "-F",
        f"issueLimit={issue_limit}",
        "-f",
        f"query={GRAPHQL_QUERY}",
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload: dict[str, Any] = json.loads(proc.stdout)
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for PR and issue triage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=("prs", "issues", "all"),
        default="prs",
        help="Triage target: 'prs' (default), 'issues', or 'all'",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo (default: %(default)s)")
    parser.add_argument("--reviewer", default=None, help="GitHub username to triage for (default: authenticated user)")
    parser.add_argument("--pr-limit", type=int, default=100, help="Max open PRs to fetch (default: %(default)s)")
    parser.add_argument("--issue-limit", type=int, default=50, help="Max open issues to fetch (default: %(default)s)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args(argv)

    include_prs = args.command in {"prs", "all"}
    include_issues = args.command in {"issues", "all"}

    data = fetch_github_data(
        args.repo,
        args.pr_limit,
        include_pr_details=include_prs,
        include_issues=include_issues,
        issue_limit=args.issue_limit,
    )
    reviewer: str = args.reviewer or data["viewer"]["login"]
    repo_data = data["repository"]

    pr_nodes = [n for n in (repo_data.get("pullRequests", {}).get("nodes") or []) if isinstance(n, dict)]
    pr_numbers = {int(n["number"]) for n in pr_nodes if isinstance(n.get("number"), int)}

    prs: list[PullRequestItem] = []
    buckets: dict[str, list[PullRequestItem]] = {}
    if include_prs:
        prs = [_parse_pr(node, reviewer, pr_numbers) for node in pr_nodes]
        _populate_overlaps(prs)
        buckets = classify_prs(prs, reviewer)

    issues: list[IssueItem] = []
    if include_issues:
        prs_by_issue: dict[int, list[int]] = {}
        for pr_node in pr_nodes:
            if bool(pr_node.get("isDraft")):
                continue
            pr_num = int(pr_node["number"])
            for issue_num in _extract_issue_refs(pr_node, pr_numbers):
                prs_by_issue.setdefault(issue_num, []).append(pr_num)
        issue_nodes = [n for n in (repo_data.get("issues", {}).get("nodes") or []) if isinstance(n, dict)]
        issues = [
            IssueItem(
                number=int(node["number"]),
                title=str(node.get("title") or ""),
                url=str(node.get("url") or ""),
                author=_login(node),
                created_at=str(node.get("createdAt") or ""),
                labels=[
                    lbl["name"]
                    for lbl in (node.get("labels", {}).get("nodes") or [])
                    if isinstance(lbl, dict) and isinstance(lbl.get("name"), str)
                ],
                comment_count=int((node.get("comments") or {}).get("totalCount") or 0),
                linked_prs=sorted(prs_by_issue.get(int(node["number"]), [])),
            )
            for node in issue_nodes
        ]

    if args.json:
        out: dict[str, Any] = {"reviewer": reviewer}
        if include_prs:
            out["buckets"] = {k: [asdict(p) for p in v] for k, v in buckets.items()}
            out["recommended_batch"] = [p.number for p in recommend_batch(buckets)]
        if include_issues:
            out["issues"] = [asdict(i) for i in issues]
        print(json.dumps(out, indent=2))
    else:
        md_lines: list[str] = []
        if include_prs:
            md_lines.extend(_render_prs_markdown(reviewer, prs, buckets))
        if include_issues:
            md_lines.extend(_render_issues_markdown(args.repo, issues))
        print("\n".join(md_lines).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
