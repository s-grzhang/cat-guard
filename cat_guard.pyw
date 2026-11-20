"""Cat Guard: blocks keyboard input when a cat is on the keyboard.

Run from an administrator terminal:  python cat_guard.pyw
Ctrl+Alt+M  pause / resume detection
Ctrl+Alt+Q  quit
Ctrl+Alt+Del always works (Windows never lets programs block it).
"""
import threading
import time

import keyboard

# Thresholds from your recorded data
PAW_KEYS = 8      # this many keys down at once = instant lock (your max: 6)
MAX_KEYS = 4      # a "paw-sized" group
HOLD_SECS = 0.2   # 4+ keys held this long = lock (your longest: 0.064s)
QUIET_SECS = 3    # unlock after this long with no key presses

# Gaming keys you hold down on purpose. They don't count toward the
# 4-key hold rule, but they still count toward PAW_KEYS, so a cat
# lying across them still gets caught.
# Scan codes: W=17, A=30, S=31, D=32, Left Shift=42, Space=57, Left Ctrl=29
GAME_KEYS = {17, 30, 31, 32, 42, 57, 29}

held = set()        # scan codes currently down
passed = set()      # keys whose "down" reached your apps
group_start = None  # when 4+ keys first became held together
last_press = 0.0
locked = False
paused = False
lock = threading.Lock()


def set_locked(value):
    global locked
    if locked != value:
        locked = value
        print("Cat detected, keyboard locked" if value else "Keyboard unlocked")


def check_group(now):
    """Lock if the current group of keys looks like a paw."""
    if len(held) >= PAW_KEYS:
        set_locked(True)
    elif group_start is not None and now - group_start >= HOLD_SECS:
        set_locked(True)


def on_event(e):
    global group_start, last_press, paused
    now = time.time()
    code = e.scan_code

    with lock:
        if e.event_type == "down":
            # Your shortcuts, checked before anything else
            if keyboard.is_pressed("ctrl") and keyboard.is_pressed("alt"):
                if e.name == "m":
                    paused = not paused
                    set_locked(False)
                    print("⏸ Paused" if paused else "▶ Watching for cats")
                    return False
                if e.name == "q":
                    print("Bye!")
                    keyboard.unhook_all()
                    raise SystemExit
            last_press = now
            held.add(code)  # sets ignore auto-repeat duplicates
        else:
            held.discard(code)

        if paused:
            return True

        # Track how long 4+ keys have been down together
        if len(held - GAME_KEYS) >= MAX_KEYS:
            if group_start is None:
                group_start = now
        else:
            group_start = None

        check_group(now)

        if e.event_type == "up":
            # Always release keys your apps saw go down, so nothing gets stuck
            if code in passed:
                passed.discard(code)
                return True
            return not locked

        if locked:
            return False
        passed.add(code)
        return True


def watchdog():
    """Lock while a cat sits still; unlock once it leaves."""
    while True:
        time.sleep(0.05)
        with lock:
            if paused:
                continue
            now = time.time()
            if not locked:
                check_group(now)
            elif not held and now - last_press > QUIET_SECS:
                set_locked(False)


threading.Thread(target=watchdog, daemon=True).start()
keyboard.hook(on_event, suppress=True)
print("Cat Guard running. Ctrl+Alt+M to pause, Ctrl+Alt+Q to quit.")
keyboard.wait()