"""Analyze keylog.csv: you vs. the cat.

Usage:  python analyze_keys.py
Labels named 'cat' count as cat; everything else counts as human.
"""
import pandas as pd

MAX_KEYS = 4  # what counts as a "paw-sized" group

df = pd.read_csv("keylog.csv").sort_values(["session", "t"]).reset_index(drop=True)

# --- How long each key was held -------------------------------------------
df["n"] = df.groupby(["session", "key", "event"]).cumcount()
downs = df[df.event == "down"]
ups = df[df.event == "up"]
holds = downs.merge(ups, on=["session", "label", "key", "n"], suffixes=("_down", "_up"))
holds["hold_s"] = holds.t_up - holds.t_down

# --- How long 4+ keys stayed down together ---------------------------------
df["big"] = df.n_held >= MAX_KEYS
df["run"] = (df.big != df.groupby("session").big.shift()).cumsum()
runs = df.groupby(["session", "label", "run"]).agg(big=("big", "first"), start=("t", "first")).reset_index()
runs["end"] = runs.groupby("session").start.shift(-1)
groups = runs[runs.big].dropna(subset=["end"]).copy()
groups["group_s"] = groups.end - groups.start

# --- Summary per label -------------------------------------------------------
summary = pd.DataFrame({
    "max_keys_at_once": df.groupby("label").n_held.max(),
    "longest_key_hold_s": holds.groupby("label").hold_s.max(),
    "median_key_hold_s": holds.groupby("label").hold_s.median(),
    "groups_of_4plus": groups.groupby("label").size(),
    "longest_group_s": groups.groupby("label").group_s.max(),
}).fillna(0).round(3)

print("\n=== Summary by label ===")
print(summary.to_string())

# --- Suggest a HOLD_SECS threshold ------------------------------------------
human = groups[groups.label != "cat"].group_s
cat = groups[groups.label == "cat"].group_s
if len(cat) and len(human):
    hi_h, lo_c = human.max(), cat.median()
    print(f"\nLongest human 4+ group: {hi_h:.3f}s   Typical cat group: {lo_c:.3f}s")
    if hi_h < lo_c:
        print(f"Suggested HOLD_SECS = {(hi_h + lo_c) / 2:.2f}")
    else:
        print("Overlap! Try a higher MAX_KEYS, or collect more cat data.")
elif not len(cat):
    print("\nNo cat groups yet. Record a session with:  python log_keys.py cat")

# Dataframes for your own digging (e.g. in a notebook): df, holds, groups
