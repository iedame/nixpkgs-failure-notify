#!/usr/bin/env python3

from pathlib import PurePath

import glob
import json
import os
import subprocess

def run_gh(args, gh_token):
    env = {**os.environ, "GH_TOKEN": gh_token}

    result = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        print("gh command failed:")
        print(" ".join(["gh", *args]))
        print("stdout:")
        print(result.stdout)
        print("stderr:")
        print(result.stderr)

        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=result.args,
            output=result.stdout,
            stderr=result.stderr,
        )

    return result

def find_issue_by_title(repo, branch, pkg, gh_token):
    result = run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f"{branch} {pkg} in:title",
            "--limit",
            "10",
            "--json",
            "number,title,state",
        ],
        gh_token,
    )

    issues = json.loads(result.stdout)
    expected_title = f"[{branch}] {pkg} build failures"

    for issue in issues:
        if issue["title"] == expected_title:
            return issue

    return None

def close_issue(repo, issue_number, gh_token):
    run_gh(
        [
            "issue",
            "close",
            str(issue_number),
            "--repo",
            repo,
        ],
        gh_token,
    )

def reopen_issue(repo, issue_number, gh_token):
    run_gh(
        [
            "issue",
            "reopen",
            str(issue_number),
            "--repo",
            repo,
        ],
        gh_token,
    )

def add_issue_comment(repo, issue_number, body, gh_token):
    run_gh(
        [
            "issue",
            "comment",
            str(issue_number),
            "--repo",
            repo,
            "--body",
            body,
        ],
        gh_token,
    )

def sync_issues(branch="trunk"):
    with open(f"results/{branch}/concerned-failures.json") as f:
        rows = json.load(f)

    with open(f"previous-{branch}.json") as f:
        known_fails = {row[0] for row in json.load(f)}

    current_fails = {row[0] for row in rows}

    supported_systems = tuple(
        f"{arch}-{system}"
        for system in ("linux", "darwin")
        for arch in ("x86_64", "aarch64")
    )

    repo = os.getenv("GH_REPOSITORY")
    assert repo is not None

    gh_token = os.getenv("GH_TOKEN")
    assert gh_token is not None

    recovered_packages = known_fails - current_fails

    for pkg in recovered_packages:
        issue = find_issue_by_title(repo, branch, pkg, gh_token)

        if issue is None:
            print(f"No issue found for recovered package: {pkg}")
            continue

        if issue["state"] == "OPEN":
            print(f"Closing resolved issue #{issue['number']}: {pkg}")
            close_issue(repo, issue["number"], gh_token)
        else:
            print(f"Issue #{issue['number']} is already closed: {pkg}")

    print("Processing", len(rows), "items")

    for row in rows:
        pkg = row[0]

        if pkg in known_fails:
            print("Skipping", pkg, "(known)")
            continue

        failures = [
            f"- [ ] `{platform}`: "
            f"[log](https://hydra.nixos.org/build/{build_id}/log)"
            for platform, build_id in zip(supported_systems, row[1:])
            if build_id
        ]

        if not failures:
            continue

        body = (
            "@iedame\n\n"
            + f"Build failures for `{pkg}`:\n\n"
            + "\n".join(failures)
        )

        title = f"[{branch}] {pkg} build failures"
        issue = find_issue_by_title(repo, branch, pkg, gh_token)

        if issue is not None:
            issue_number = issue["number"]

            if issue["state"] == "CLOSED":
                print(f"Reopening resolved issue #{issue_number}: {title}")
                reopen_issue(repo, issue_number, gh_token)

            print(f"Updating existing issue #{issue_number}: {title}")
            add_issue_comment(repo, issue_number, body, gh_token)
            continue

        print(f"Creating issue: {title}")

        run_gh(
            [
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
            ],
            gh_token,
        )

if __name__ == "__main__":
    for failure_path in glob.glob("results/*/concerned-failures.json"):
        branch = PurePath(failure_path).parts[-2]
        sync_issues(branch=branch)
