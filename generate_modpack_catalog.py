#!/usr/bin/env python3
"""Generate a categorized, version-verified Minecraft Forge mod catalog.

Uses the public Modrinth API. The output is a download catalog, not a tested
or launcher-importable modpack; manual conflict and dependency review remains
necessary before installing a large collection of mods.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://api.modrinth.com/v2"
GAME_VERSION = "1.20.1"
LOADER = "forge"
TARGET_PER_CATEGORY = 1000
OUTPUT_FILE = Path("forge_1.20.1_mod_catalog.txt")
USER_AGENT = "Forge1201ModCatalog/1.0 (personal modpack research)"

# Modrinth categories are tags, not mutually exclusive buckets. These rules
# classify projects into the requested broad labels using tags and metadata.
CATEGORY_TAGS = {
    "Weapons": {"equipment", "combat", "magic", "adventure"},
    "Decoration": {"decoration", "worldgen", "blocks", "cursed"},
    "Other": {"technology", "worldgen", "adventure", "cursed"},
    "Roleplay": {"social", "adventure", "decoration", "magic"},
    "Essential": {"performance", "utility", "optimization", "game-mechanics"},
    "Helper": {"library", "utility", "food", "decoration"},
    "Fun": {"cursed", "magic", "adventure", "worldgen", "combat"},
}
KEYWORDS = {
    "Weapons": ("weapon", "sword", "bow", "combat", "armor", "shield", "guns", "battle"),
    "Decoration": ("decor", "furniture", "building", "blocks", "paintings", "lighting"),
    "Other": ("technology", "worldgen", "dimension", "storage", "automation", "misc"),
    "Roleplay": ("roleplay", "role-play", "social", "npc", "dialogue", "emote", "villager"),
    "Essential": ("performance", "optimization", "utility", "fix", "essential", "quality of life", " qol "),
    "Helper": ("library", "api", "helper", "food", "map", "recipe", "tool", "inventory"),
    "Fun": ("fun", "magic", "adventure", "pets", "creature", "minigame", "cursed", "challenge"),
}
PAGE_SIZE = 100
REQUEST_DELAY_SECONDS = 0.25


def api_get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                retry_after = exc.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt
                time.sleep(min(wait, 60))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"API request failed after retries: {url}")


def project_categories(project: dict[str, Any]) -> set[str]:
    values = set(project.get("categories") or [])
    values.update(project.get("display_categories") or [])
    return values


def classify(project: dict[str, Any]) -> list[str]:
    tags = project_categories(project)
    text = " ".join((project.get("title", ""), project.get("description", ""))).lower()
    assigned = []
    for category in CATEGORY_TAGS:
        if tags.intersection(CATEGORY_TAGS[category]) or any(word in text for word in KEYWORDS[category]):
            assigned.append(category)
    return assigned


def search_projects(offset: int) -> list[dict[str, Any]]:
    facets = [["project_type:mod"], [f"versions:{GAME_VERSION}"], [f"categories:{LOADER}"]]
    params = {
        "facets": json.dumps(facets, separators=(",", ":")),
        "limit": str(PAGE_SIZE),
        "offset": str(offset),
        "index": "downloads",
    }
    result = api_get("/search", params)
    return result.get("hits", [])


def compatible_version(project_id: str) -> dict[str, Any] | None:
    params = {"game_versions": json.dumps([GAME_VERSION]), "loaders": json.dumps([LOADER])}
    versions = api_get(f"/project/{urllib.parse.quote(project_id, safe='')}/version", params)
    for version in versions:
        if GAME_VERSION not in version.get("game_versions", []):
            continue
        if LOADER not in version.get("loaders", []):
            continue
        if version.get("status") not in (None, "listed"):
            continue
        files = version.get("files") or []
        usable = [item for item in files if item.get("url") and item.get("filename", "").lower().endswith(".jar")]
        if usable:
            version["_selected_file"] = next((item for item in usable if item.get("primary")), usable[0])
            return version
    return None


def main() -> None:
    print(f"Searching Modrinth for {GAME_VERSION} Forge mods...")
    found: dict[str, dict[str, Any]] = {}
    memberships: dict[str, set[str]] = defaultdict(set)
    offset = 0
    pages_without_results = 0
    while True:
        hits = search_projects(offset)
        time.sleep(REQUEST_DELAY_SECONDS)
        if not hits:
            pages_without_results += 1
            break
        for project in hits:
            pid = project.get("project_id")
            if not pid:
                continue
            categories = classify(project)
            for category in categories:
                if len(memberships[category]) < TARGET_PER_CATEGORY:
                    memberships[category].add(pid)
            found.setdefault(pid, project)
        offset += len(hits)
        print(f"  Discovered {len(found)} projects; checked search offset {offset}.")
        if len(hits) < PAGE_SIZE:
            break
        if all(len(memberships[name]) >= TARGET_PER_CATEGORY for name in CATEGORY_TAGS):
            break
        # The API search index is paginated; keep progress bounded if catalog facets are broad.
        if offset >= 10_000:
            print("  Search offset limit reached; stopping safely.")
            break

    selected_ids = set().union(*memberships.values()) if memberships else set()
    verified: dict[str, dict[str, Any]] = {}
    for number, pid in enumerate(sorted(selected_ids), 1):
        project = found[pid]
        try:
            version = compatible_version(pid)
        except Exception as exc:
            print(f"  Skipping {project.get('title', pid)}: version lookup failed ({exc}).")
            continue
        time.sleep(REQUEST_DELAY_SECONDS)
        if version is None:
            continue
        file_info = version.pop("_selected_file")
        verified[pid] = {
            "project": project,
            "version": version,
            "file": file_info,
            "categories": sorted(category for category in memberships if pid in memberships[category]),
        }
        if number % 100 == 0:
            print(f"  Verified versions for {number}/{len(selected_ids)} candidates.")

    final_categories: dict[str, list[str]] = {}
    for category in CATEGORY_TAGS:
        ids = [pid for pid in memberships[category] if pid in verified]
        final_categories[category] = sorted(ids, key=lambda pid: (
            -int(found[pid].get("downloads", 0)), found[pid].get("title", "").casefold()
        ))[:TARGET_PER_CATEGORY]

    lines = [
        f"Minecraft {GAME_VERSION} | Forge | Modrinth verified-version catalog",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "IMPORTANT: This is a catalog, not a tested modpack. Each listed file has a",
        "published Modrinth version declaring Forge and Minecraft 1.20.1 support.",
        "Compatibility between mods, required dependencies, client/server side, and",
        "runtime behavior are not guaranteed by metadata alone. Review dependencies",
        "and test a small set before using the catalog in a world or server.",
        "",
    ]
    for category in CATEGORY_TAGS:
        ids = final_categories[category]
        lines.append(f"[{category}] {len(ids)} verified entries (target: {TARGET_PER_CATEGORY})")
        for pid in ids:
            entry = verified[pid]
            project, version, file_info = entry["project"], entry["version"], entry["file"]
            lines.append(
                f"- {project.get('title', pid)} | {version.get('version_number', version.get('id', 'unknown'))}"
            )
            lines.append(f"  Project: https://modrinth.com/mod/{project.get('slug', pid)}")
            lines.append(f"  Download: {file_info['url']}")
            lines.append(f"  File: {file_info.get('filename', 'unknown')} | {file_info.get('size', 0)} bytes")
            required = [d.get("project_id") or d.get("file_name") for d in version.get("dependencies", [])
                        if d.get("dependency_type") == "required"]
            if required:
                lines.append("  Required dependencies to review: " + ", ".join(x for x in required if x))
        lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.resolve()}")
    print("Verified entry counts:")
    for category, ids in final_categories.items():
        print(f"  {category}: {len(ids)}/{TARGET_PER_CATEGORY}")
    total_unique = len(set().union(*(set(ids) for ids in final_categories.values())))
    print(f"Unique verified mods across categories: {total_unique}")
    if any(len(ids) < TARGET_PER_CATEGORY for ids in final_categories.values()):
        print("The requested 1,000-per-category quota was not available in the verified catalog.")


if __name__ == "__main__":
    main()
