#!/usr/bin/env python3
"""One-shot script to move existing MEGA root files into organized subdirectories."""

import asyncio
import os
import sys
import types

# mega.py needs this on newer Python
if not hasattr(asyncio, "coroutine"):
    asyncio.coroutine = types.coroutine

from mega import Mega

EMAIL = os.environ.get("MEGA_EMAIL", "")
PASSWORD = os.environ.get("MEGA_PASSWORD", "")

if not EMAIL or not PASSWORD:
    print("Set MEGA_EMAIL and MEGA_PASSWORD env vars")
    sys.exit(1)

m = Mega()
client = m.login(EMAIL, PASSWORD)

files = client.get_files()

# Find target folder nodes
audioprompts_folder = client.find("audioprompts")
survey_folder = client.find("survey")

if not audioprompts_folder:
    print("ERROR: /Root/audioprompts folder not found on MEGA")
    sys.exit(1)
if not survey_folder:
    print("ERROR: /Root/survey folder not found on MEGA")
    sys.exit(1)

# Get the root folder node ID
root_id = None
for node_id, node in files.items():
    if node["t"] == 2:  # root folder type
        root_id = node_id
        break

if not root_id:
    print("ERROR: Could not find MEGA root folder")
    sys.exit(1)

audioprompts_id = list(audioprompts_folder.keys())[0] if isinstance(audioprompts_folder, dict) else audioprompts_folder
survey_id = list(survey_folder.keys())[0] if isinstance(survey_folder, dict) else survey_folder

moved_audio = 0
moved_survey = 0
skipped = 0

for node_id, node in files.items():
    if node.get("p") != root_id:
        continue
    if node.get("t") != 0:  # only files
        continue

    name = node.get("a", {}).get("n", "")
    if not name:
        continue

    if name.startswith("survey_feedback") or name.startswith("example_report"):
        try:
            client.move(node_id, survey_id)
            moved_survey += 1
            if moved_survey % 10 == 0:
                print(f"  Moved {moved_survey} survey files...")
        except Exception as e:
            print(f"  WARN: Failed to move {name}: {e}")
    elif name.endswith(".wav") or name.endswith(".json"):
        try:
            client.move(node_id, audioprompts_id)
            moved_audio += 1
            if moved_audio % 100 == 0:
                print(f"  Moved {moved_audio} audio files...")
        except Exception as e:
            print(f"  WARN: Failed to move {name}: {e}")
    else:
        skipped += 1

print(f"\nDone! Moved {moved_audio} files to audioprompts, {moved_survey} to survey, skipped {skipped}")
