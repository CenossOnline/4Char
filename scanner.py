#!/usr/bin/env python3
"""
4CHAR continuous Minecraft 4-character username scanner.

Loop:
    1. Discover new names for 30 minutes.
    2. Add discoveries to the existing database.
    3. Verify every name in the database.
    4. Remove names that are no longer available.
    5. Repeat forever.

The local database is data/names.json.

If GITHUB_TOKEN is set, every completed phase is also synced to GitHub.
That lets the Cloudflare deployment pick up the new database automatically.
"""

import base64
import json
import os
import random
import sys
import time
from itertools import product
from pathlib import Path

import requests

VOWELS = set("aeiou")
LETTERS = "abcdefghijklmnopqrstuvwxyz"
RARE = set("qxzj")

START_CLUSTERS = {
    "bl", "br", "ch", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr",
    "sc", "sh", "sk", "sl", "sm", "sn", "sp", "st", "sw", "th", "tr", "tw",
}

END_CLUSTERS = {
    "ck", "ft", "ld", "lf", "lk", "lm", "lp", "lt", "mp", "nd", "ng", "nk",
    "nt", "rd", "rk", "rm", "rn", "rp", "rt", "sk", "sp", "st", "sh", "th",
}

DATABASE_FILE = Path("data/names.json")
DISCOVERY_SECONDS = 30 * 60
REQUEST_DELAY = 1.0
API_URL = "https://api.minecraftservices.com/minecraft/profile/lookup/name/{}"

GITHUB_API = "https://api.github.com"
GITHUB_REPO = os.getenv("GITHUB_REPO", "CenossOnline/4Char")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

INITIAL_NAMES = [
    "oyim",
    "oyih",
    "ufuv",
    "iyey",
    "uwiv",
    "wiyi",
    "goiw",
    "uyeg",
    "doaf",
]


def is_clean(name: str, allow_rare: bool = False) -> bool:
    if len(name) != 4 or not name.isalpha():
        return False

    if not allow_rare and any(c in RARE for c in name):
        return False

    if len(set(name)) < 3:
        return False

    if any(name[i] == name[i + 1] == name[i + 2] for i in range(2)):
        return False

    pattern = "".join("V" if c in VOWELS else "C" for c in name)

    if pattern in ("CVCV", "VCVC", "CVVC"):
        if pattern == "CVVC" and name[1:3] not in {
            "ea", "ee", "oo", "ai", "ay", "oa", "ou", "ie", "ow", "oi"
        }:
            return False
        return True

    if pattern == "CCVC":
        return name[:2] in START_CLUSTERS

    if pattern == "CVCC":
        return name[2:] in END_CLUSTERS

    return False


def generate_candidates():
    candidates = [
        "".join(p)
        for p in product(LETTERS, repeat=4)
        if is_clean("".join(p))
    ]
    random.shuffle(candidates)
    return candidates


def load_database():
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DATABASE_FILE.exists():
        names = sorted(set(INITIAL_NAMES))
        save_database(names)
        return names

    try:
        with DATABASE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            names = data.get("names", [])
        else:
            names = data

        names = sorted({
            str(name).lower()
            for name in names
            if isinstance(name, str) and len(name) == 4 and name.isalpha()
        })

        save_database(names)
        return names

    except (OSError, json.JSONDecodeError) as exc:
        print(f"! Could not read {DATABASE_FILE}: {exc}")
        print("  Keeping the existing database untouched.")
        return []


def save_database(names):
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = DATABASE_FILE.with_suffix(".json.tmp")

    data = {
        "updated_at": int(time.time()),
        "names": sorted(set(names)),
    }

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    temp_file.replace(DATABASE_FILE)


def sync_database_to_github():
    """Push the completed database to GitHub when a token is configured."""
    if not GITHUB_TOKEN:
        print("  ! GITHUB_TOKEN is not set; database remains local.")
        return False

    try:
        with DATABASE_FILE.open("rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        path = "data/names.json"
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{path}"

        current = requests.get(
            url,
            headers=headers,
            params={"ref": GITHUB_BRANCH},
            timeout=20,
        )

        if current.status_code not in (200, 404):
            print(f"  ! GitHub read failed: HTTP {current.status_code}")
            return False

        payload = {
            "message": "Update 4CHAR username database",
            "content": content,
            "branch": GITHUB_BRANCH,
        }

        if current.status_code == 200:
            payload["sha"] = current.json()["sha"]

        response = requests.put(url, headers=headers, json=payload, timeout=20)

        if response.status_code not in (200, 201):
            print(f"  ! GitHub sync failed: HTTP {response.status_code}")
            print(f"    {response.text[:300]}")
            return False

        print("  [✓] Database synced to GitHub.")
        return True

    except requests.RequestException as exc:
        print(f"  ! GitHub sync error: {exc}")
        return False


def check_available(name, session):
    """
    True  = available
    False = taken
    None  = error/rate limited
    """
    try:
        response = session.get(API_URL.format(name), timeout=10)
    except requests.RequestException as exc:
        print(f"  ! network error on {name}: {exc}")
        return None

    if response.status_code == 200:
        return False

    if response.status_code == 404:
        return True

    if response.status_code == 429:
        return None

    print(f"  ! unexpected HTTP {response.status_code} for {name}")
    return None


def check_with_backoff(name, session):
    backoff = 30

    while True:
        result = check_available(name, session)

        if result is not None:
            return result

        print(f"  rate limited/error for {name}; sleeping {backoff}s...")
        time.sleep(backoff)
        backoff = min(backoff * 2, 300)


def discover_for_30_minutes(database, session):
    print("\n=== NEW NAME DISCOVERY: 30 MINUTES ===")

    candidates = generate_candidates()
    database_set = set(database)
    start = time.monotonic()
    found = []

    for candidate in candidates:
        if time.monotonic() - start >= DISCOVERY_SECONDS:
            break

        if candidate in database_set:
            continue

        result = check_with_backoff(candidate, session)

        if result:
            found.append(candidate)
            database_set.add(candidate)
            print(f"  [+] AVAILABLE: {candidate}")

        remaining = DISCOVERY_SECONDS - (time.monotonic() - start)
        if remaining <= 0:
            break

        time.sleep(min(REQUEST_DELAY, remaining))

    print(f"\nDiscovery finished. Found {len(found)} new names.")
    return found


def verify_database(database, session):
    print(f"\n=== VERIFYING DATABASE: {len(database)} NAMES ===")

    kept = []

    for index, name in enumerate(database, 1):
        result = check_with_backoff(name, session)

        if result:
            kept.append(name)
            print(f"  [{index}/{len(database)}] KEEP: {name}")
        else:
            print(f"  [{index}/{len(database)}] REMOVE: {name}")

        time.sleep(REQUEST_DELAY)

    return kept


def main():
    print("4CHAR scanner starting...")

    database = load_database()
    print(f"Loaded {len(database)} names.")

    if GITHUB_TOKEN:
        print(f"GitHub sync enabled: {GITHUB_REPO}")
    else:
        print("GitHub sync disabled: set GITHUB_TOKEN to publish updates.")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "4CHAR-name-scanner/1.0"
    })

    try:
        while True:
            # 30-minute discovery phase.
            new_names = discover_for_30_minutes(database, session)

            # Merge only. Existing names are never overwritten here.
            database = sorted(set(database) | set(new_names))
            save_database(database)
            print(f"Database now contains {len(database)} names.")
            sync_database_to_github()

            # Full verification phase.
            database = verify_database(database, session)
            save_database(database)
            print(f"Verification complete. {len(database)} names remain.")
            sync_database_to_github()

    except KeyboardInterrupt:
        print("\nStopped safely.")
        save_database(database)
        sync_database_to_github()
        print(f"Saved {len(database)} names before exiting.")


if __name__ == "__main__":
    sys.exit(main())
