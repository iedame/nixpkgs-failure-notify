#!/usr/bin/env python3

from pathlib import PurePath

import glob
import json
import subprocess
import os

def run_gh(args, gh_token):
    env = {**os.environ, "GH_TOKEN": gh_token}

    return subprocess.run(
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
            result.returncode,
            result.args,
            result.stdout,
            result.stderr,
        )

    return result

def find_issue_by_title(repo, title, gh_token):
    result = run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f'"{title}" in:title',
            "--limit",
            "10",
            "--json",
            "number",
            "title",
        ],
        gh_token,
    )

    issues = json.loads(result.stdout)

    for issue in issues:
        if issue["title"] == title:
            return issue["number"]

    return None

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

def create_issues(branch="trunk"):
    with open(f"results/{branch}/concerned-failures.json") as f:
        rows = json.load(f)

    with open(f"previous-{branch}.json") as f:
        known_fails = [r[0] for r in json.load(f)]


    SUPPORTED_SYSTEMS = tuple(
        f"{arch}-{sys}"
        for sys in ("linux", "darwin")
        for arch in ("x86_64", "aarch64")
    )

    repo = os.getenv("GH_REPOSITORY")
    assert repo is not None

    gh_token = os.getenv("GH_TOKEN")
    assert gh_token is not None


    print("Processing", len(rows), "items")
    for row in rows:
        pkg = row[0]
        if pkg in known_fails:
            print("Skipping", pkg, "(known)")
            continue

        failures = [
            f"- [ ] `{plat}`: [log](https://hydra.nixos.org/build/{build_id}/log)"
            for plat, build_id in zip(SUPPORTED_SYSTEMS, row[1:])
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

        issue_number = find_issue_by_title(repo, title, gh_token)

        if issue_number is not None:
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
        create_issues(branch=branch)
