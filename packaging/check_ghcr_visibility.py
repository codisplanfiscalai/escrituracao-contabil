"""Read-only gate for an existing GHCR package, using the workflow token only."""
import argparse
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def check(repository, owner_type, token, *, allow_missing=False):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository name")
    if owner_type not in {"User", "Organization"}:
        raise ValueError("Unknown repository owner type")
    owner, name = repository.lower().split("/")
    prefix = "users" if owner_type == "User" else "orgs"
    url = f"https://api.github.com/{prefix}/{quote(owner)}/packages/container/{quote(name, safe='')}"
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                    "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urlopen(request, timeout=30) as response:
            package = json.load(response)
    except HTTPError as error:
        if error.code == 404 and allow_missing:
            print("Package absent or inaccessible; GitHub defaults new packages to private. Publication must still succeed and pass the post-check.")
            return
        raise RuntimeError(f"GHCR visibility verification failed (HTTP {error.code}); stop further steps. "
                           "If a push already completed, inspect the existing package before retrying.") from None
    if package.get("visibility") != "private":
        raise ValueError("GHCR package must be private; stop further steps. This workflow never changes visibility. "
                         "If a push already completed, inspect the existing package before retrying.")
    print("PASS: existing GHCR package visibility is private")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    check(os.environ["GITHUB_REPOSITORY"], os.environ["REPOSITORY_OWNER_TYPE"], os.environ["GH_TOKEN"],
          allow_missing=args.allow_missing)
