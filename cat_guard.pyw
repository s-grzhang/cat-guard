"""Cat Guard: blocks keyboard input when a cat is on the keyboard.

Run:  pythonw cat_guard.pyw   (as administrator, or via Task Scheduler)
Ctrl+Alt+M  pause / resume detection
Ctrl+Alt+Q  quit
Ctrl+Alt+Del always works (Windows never lets programs block it).
Events are logged to cat_guard.log next to this file.
"""
import logging
import os
import threading
import time

import keyboard

# ---- Settings ---------------------------------------------------------------
CHORD_KEYS = 4        # this many typing keys down at once = lock instantly
PAW_KEYS = 8          # this many keys of any kind down at once = lock instantly
LONG_HOLD_SECS = 1.0  # a typing key held this long = lock
QUIET_SECS = 3.0      # unlock after this long with no key activity

# Keys people hold down on purpose. They never count as "typing keys",
# so they don't trigger the chord or long-hold rules, and they auto-repeat
# normally. (They still count toward PAW_KEYS.)
HOLDABLE = {
    17, 30, 31, 32,      # W A S D
    42, 54,              # Left / Right Shift
    29,                  # Ctrl (both)
    56,                  # Alt (both)
    91, 92,              # Windows keys
    57,                  # Space
    14, 83,              # Backspace, Delete
    72, 75, 77, 80,      # Arrow keys
    15,                  # Tab
    71, 79,              # Home, End
    73, 81,              # Page Up, Page Down
    28,                  # Enter
    1,                   # Esc
}
CTRL, ALT, KEY_M, KEY_Q = 29, 56, 50, 16

# ---- Logging (pythonw has no console) ----------------------------------------
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cat_guard.log"),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
log = logging.getLogger("cat_guard")

# ---- State --------------------------------------------------------------------
down_since = {}   # scan code -> when it was first pressed
passed = set()    # keys whose press reached your apps (their release must too)
last_activity = 0.0
locked = False
paused = False
state_lock = threading.Lock()
running = threading.Event()
running.set()


def set_locked(value, reason=""):
    global locked
    if locked != value:
        locked = value
        log.info("LOCKED (%s)" % reason if value else "unlocked")


def check_for_cat(now):
    """Lock if what's held down looks like a cat."""
    if locked:
        return
    typing_keys = [c for c in down_since if c not in HOLDABLE]
    if len(down_since) >= PAW_KEYS:
        set_locked(True, "%d keys down" % len(down_since))
    elif len(typing_keys) >= CHORD_KEYS:
        set_locked(True, "%d typing keys down" % len(typing_keys))
    else:
        for c in typing_keys:
            if now - down_since[c] >= LONG_HOLD_SECS:
                set_locked(True, "key %d held %.1fs" % (c, now - down_since[c]))
                break


def handle(e):
    """Return True to let the key through, False to block it."""
    global last_activity, paused
    now = time.monotonic()
    code = e.scan_code

    if e.event_type == "down":
        repeat = code in down_since
        if not repeat:
            down_since[code] = now
        last_activity = now

        # Your shortcuts work even while locked
        if not repeat and CTRL in down_since and ALT in down_since:
            if code == KEY_M:
                paused = not paused
                set_locked(False)
                log.info("paused" if paused else "resumed")
                return False
            if code == KEY_Q:
                log.info("quit")
                running.clear()
                return False

        if paused:
            passed.add(code)
            return True

        check_for_cat(now)
        if locked:
            return False
        # Typing keys don't auto-repeat, so a cat leaning on one key types
        # one letter instead of a whole line before the lock kicks in.
        if repeat and code not in HOLDABLE:
            return False
        passed.add(code)
        return True

    # key released
    down_since.pop(code, None)
    last_activity = now
    if code in passed:
        passed.discard(code)
        return True
    return paused or not locked


def on_event(e):
    with state_lock:
        try:
            return handle(e)
        except Exception:
            # Never let a bug in here freeze your keyboard
            log.exception("error handling key event")
            return True


def watchdog():
    """Catch keys held without new events, and unlock once the cat is gone."""
    while running.is_set():
        time.sleep(0.05)
        with state_lock:
            if paused:
                continue
            now = time.monotonic()
            if not locked:
                check_for_cat(now)
            elif now - last_activity > QUIET_SECS:
                # A key that's really held keeps sending repeat presses, so
                # silence means anything still "down" is a missed release.
                down_since.clear()
                set_locked(False)


log.info("started")
threading.Thread(target=watchdog, daemon=True).start()
keyboard.hook(on_event, suppress=True)
while running.is_set():  # keep running until Ctrl+Alt+Q
    time.sleep(0.5)
keyboard.unhook_all()
log.info("stopped")
