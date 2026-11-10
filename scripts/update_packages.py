#!/usr/bin/env python3
"""Bump specs from upstream GitHub releases and rebuild them in Copr."""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "packages.json"
PACKAGER_FALLBACK = "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"


def run(cmd, check=True):
    print("+ " + " ".join(cmd), flush=True)
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def gh_api(endpoint, jq):
    result = subprocess.run(
        ["gh", "api", endpoint, "--jq", jq],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def latest_version(package):
    upstream = package["upstream"]
    tag = gh_api(f"repos/{upstream}/releases/latest", ".tag_name")
    if not tag:
        tag = gh_api(f"repos/{upstream}/tags?per_page=1", ".[0].name")
    if not tag:
        raise RuntimeError(f"no release or tag found for {upstream}")

    prefix = package.get("tag_prefix", "")
    if prefix and tag.startswith(prefix):
        tag = tag[len(prefix):]
    if not tag:
        raise RuntimeError(f"empty version after stripping prefix from {upstream}")
    return tag


def current_version(spec):
    result = run(["rpmspec", "-q", "--srpm", "--qf", "%{VERSION}", str(spec)])
    return result.stdout.strip()


def bump_spec(spec_path, version, packager):
    text = spec_path.read_text()
    text, version_count = re.subn(
        r"^Version:\s*.*$", f"Version:        {version}", text, count=1, flags=re.M
    )
    text, release_count = re.subn(
        r"^Release:\s*.*$", "Release:        1%{?dist}", text, count=1, flags=re.M
    )
    if version_count != 1 or release_count != 1:
        raise RuntimeError(f"could not update Version/Release in {spec_path}")
    if "%changelog" not in text:
        raise RuntimeError(f"no %changelog in {spec_path}")

    today = datetime.date.today().strftime("%a %b %d %Y")
    entry = f"* {today} {packager} - {version}-1\n- Update to {version}\n"
    text = re.sub(r"^%changelog\s*$", f"%changelog\n{entry}", text, count=1, flags=re.M)
    spec_path.write_text(text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("COPR_CONFIG"):
        print("COPR_CONFIG is not set; skipping auto-update")
        return 0

    manifest = json.loads(MANIFEST.read_text())
    packager = os.environ.get("PACKAGER") or PACKAGER_FALLBACK
    changes = []

    for package in manifest["packages"]:
        spec_path = ROOT / package["spec"]
        latest = latest_version(package)
        current = current_version(spec_path)

        if latest == current:
            print(f"{package['name']}: up to date ({current})")
            continue

        print(f"{package['name']}: {current} -> {latest}")
        if not args.dry_run:
            bump_spec(spec_path, latest, packager)
        changes.append((package, latest))

    if not changes:
        return 0

    if args.dry_run:
        print("dry run: not committing or building")
        return 0

    run(["git", "add"] + [str(ROOT / package["spec"]) for package, _ in changes])
    message = "Update " + ", ".join(f"{p['name']} to {v}" for p, v in changes)
    run(["git", "commit", "-m", message])
    run(["git", "push"])

    for package, _ in changes:
        run(
            [
                "copr-cli",
                "build-package",
                package["copr_project"],
                "--name",
                package["copr_package"],
                "--enable-net",
                "on",
            ]
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
