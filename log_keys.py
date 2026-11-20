"""Record raw keystrokes to keylog.csv for later analysis.

Usage:  python log_keys.py <label>
        e.g. python log_keys.py mash   (or: type, game, cat)
Press Esc to stop. Each run is appended to keylog.csv as a new session.
Nothing is blocked; this only watches.
"""
import csv
import os
import sys
import time

import keyboard

LABEL = sys.argv[1] if len(sys.argv) > 1 else "unlabeled"
OUTFILE = "keylog.csv"
SESSION = time.strftime("%Y%m%d-%H%M%S")

held = set()
rows = []


def on_event(e):
    if e.name == "esc":
        return
    # Use the physical key code, not the name: names change with Shift
    # (down "a", up "A"), which made keys look stuck.
    code = e.scan_code
    if e.event_type == "down":
        if code in held:  # skip auto-repeat
            return
        held.add(code)
    else:
        if code not in held:  # stray key-up we never saw go down
            return
        held.discard(code)
    rows.append({
        "session": SESSION,
        "label": LABEL,
        "t": time.perf_counter(),
        "event": e.event_type,
        "key": code,
        "n_held": len(held),
    })


keyboard.hook(on_event)
print(f"Logging as '{LABEL}'... press Esc to stop")
keyboard.wait("esc")
keyboard.unhook_all()

new_file = not os.path.exists(OUTFILE)
with open(OUTFILE, "a", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["session", "label", "t", "event", "key", "n_held"])
    if new_file:
        w.writeheader()
    w.writerows(rows)
print(f"Saved {len(rows)} events to {OUTFILE}")
