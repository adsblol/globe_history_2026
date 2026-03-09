# Copyright 2023 kat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import requests
import json
import os
import datetime

# This script:
# Is idempotent. It can be run multiple times without causing any issues.
# Makes a markdown list of github releases and puts it in RELEASES.md
# The list looks like this:
# - [releasename](releaselink)
# Make sure it is sorted by date (releasename is v2023-01-31-... always)
# Make sure it is in reverse order (newest first)

CURRENT_YEAR = datetime.datetime.now().year
REPO = f"adsblol/globe_history_{CURRENT_YEAR}"
RELEASES_FILE = "RELEASES.md"
PREFERRED_RELEASES_FILE = "PREFERRED_RELEASES.txt"
CURRENT_SIZE = 0

# Get all releases
# https://developer.github.com/v3/repos/releases/#list-releases-for-a-repository
# with pagination!
def get_releases(repo):
    releases = []
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}"} if os.getenv("GITHUB_TOKEN") else {}
    while True:
        r = requests.get(url,headers=headers)
        r.raise_for_status()
        releases += r.json()
        if "next" not in r.links:
            break
        url = r.links["next"]["url"]
    # Sort by date (releasename)
    releases.sort(key=lambda x: x["name"], reverse=True)
    return releases


# File should look like this:
# # 2023 February
# - 2023-02-01 [planes-staging-0 (xxx MB)](...) [planes-staging-1 (xxx MB)](...) [planes-test-0 (xxx MB)](...)
# - 2023-02-02 [planes-staging-0 (xxx MB)](...) [planes-staging-1 (xxx MB)](...) [planes-test-0 (xxx MB)](...)
# # 2023 January
# - 2023-01-31 [planes-staging-0 (xxx MB)](...) [planes-staging-1 (xxx MB)](...) [planes-test-0 (xxx MB)](...)
# - 2023-01-30 [planes-staging-0 (xxx MB)](...) [planes-staging-1 (xxx MB)](...) [planes-test-0 (xxx MB)](...)

releases = get_releases(REPO)
releases_per_day = {}
preferred_releases_per_day = {}
all_releases_per_day = {}

for release in releases:
    # Get date
    date = release["name"][1:11].replace(".", "-")
    date_with_dots = date.replace("-", ".")
    # Get pod name
    pod_name = release["name"][12:]
    # Get assets
    assets_size = 0
    for asset in release["assets"]:
        # check if it is a .tar file
        if ".tar" in asset["name"]:
            assets_size += asset["size"]
    assets = f"{assets_size // 1024 // 1024} MiB"
    CURRENT_SIZE += assets_size
    # Add to releases_per_day
    if date not in releases_per_day:
        releases_per_day[date] = []
    releases_per_day[date].append((pod_name, assets))
    # Add to preferred_releases_per_day if it is bigger than the current one
    # example:
    #link = f"https://github.com/{REPO}/releases/download/v{date_with_dots}-{pod_name}/v{date_with_dots}-{pod_name}.tar"
    # links should be from release.assets.0.browser_download_url, conctenated by string
    links = ",".join([asset["browser_download_url"] for asset in release["assets"]])
    if date not in all_releases_per_day:
        all_releases_per_day[date] = []
    all_releases_per_day[date].append([links])
    if date not in preferred_releases_per_day:
        preferred_releases_per_day[date] = (links, assets_size)
    else:
        if assets_size > preferred_releases_per_day[date][1]:
            preferred_releases_per_day[date] = (links, assets_size)


# Make header
lines = ["""# Releases"""]

# let's make some lines. split it by month, so we can put a header.
for date in releases_per_day.keys():
    year, month, _ = date.split("-")

    if f"# {year}-{month}" not in lines:
        lines.append(f"# {year}-{month}")
    line_for_today = f"- {date} "
    for pod_name, assets in releases_per_day[date]:
        date_with_dots = date.replace("-", ".")
        line_for_today += f"[{pod_name} ({assets})](https://github.com/{REPO}/releases/tag/v{date_with_dots}-{pod_name}#assets) "
    lines.append(line_for_today)

# Write to RELEASES.md
with open("RELEASES.md", "w") as f:
    f.writelines(lines+"\n" for lines in lines)

# Write to PREFERRED_RELEASES.txt
with open("PREFERRED_RELEASES.txt", "w") as f:
    f.writelines(f"{link}\n" for link, _ in preferred_releases_per_day.values())

# Get current_size in GiB
CURRENT_SIZE = CURRENT_SIZE // 1024 // 1024 // 1024

# read and Write to README.md
with open("README.md", "r") as f:
    readme = f.read()
    # line looks like:
    # adsblol/globe_history_2024 (xxx GiB)
    import re
    readme = re.sub(r"\# adsblol/globe_history_\d+ \(\d+ GiB\)", f"# adsblol/globe_history_{CURRENT_YEAR} ({CURRENT_SIZE} GiB)", readme)

with open("README.md", "w") as f:
    f.write(readme)

with open("ALL_RELEASES.txt", "w") as f:
    for date in all_releases_per_day.keys():
        for links in all_releases_per_day[date]:
            f.write(",".join(links) + "\n")
