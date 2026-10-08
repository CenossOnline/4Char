#!/usr/bin/env python3
"""
4CHAR continuous Minecraft 4-character username scanner.

Loop:
    1. Discover new names for 30 minutes.
    2. Add discoveries to the existing database.
    3. Verify every name in the database.
    4. Remove names that are no longer available.
    5. Repeat forever.

The database is stored in data/names.json and is never replaced by a
discovery scan. New names are merged into the existing database.
"""

import json
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

# These are the names currently displayed by 4CHAR.
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
            if isinstance(name, str) and len(name) == 4
        })

        # Make sure the names already on the site are never lost.
        names = sorted(set(names) | set(INITIAL_NAMES))

        save_database(names)
        return names

    except (OSError, json.JSONDecodeError) as exc:
        print(f"! Could not read {DATABASE_FILE}: {exc}")
        print("  Keeping the existing file untouched.")
        return list(INITIAL_NAMES)


def save_database(names):
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file first so an interrupted write cannot
    # leave the real database half-written.
    temp_file = DATABASE_FILE.with_suffix(".json.tmp")

    data = {
        "updated_at": int(time.time()),
        "names": sorted(set(names)),
    }

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    temp_file.replace(DATABASE_FILE)


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
        elapsed = time.monotonic() - start
        if elapsed >= DISCOVERY_SECONDS:
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

    session = requests.Session()
    session.headers.update({
        "User-Agent": "4CHAR-name-scanner/1.0"
    })

    try:
        while True:
            # Discovery phase.
            new_names = discover_for_30_minutes(database, session)

            # Merge, never overwrite.
            database = sorted(set(database) | set(new_names))
            save_database(database)
            print(f"Database now contains {len(database)} names.")

            # Verification phase.
            database = verify_database(database, session)
            save_database(database)
            print(f"Verification complete. {len(database)} names remain.")

    except KeyboardInterrupt:
        print("\nStopped safely.")
        save_database(database)
        print(f"Saved {len(database)} names before exiting.")


if __name__ == "__main__":
    sys.exit(main())
