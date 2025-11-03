# import pandas as pd

# # Load your CSV file
# df = pd.read_csv(r"C:\Users\JaramilloGroup\Documents\Python\ControlSoftware\logs\CryoTest_20251009-112441.csv", sep=",")

# # Convert DateTime strings to pandas Timestamps
# df['datetime'] = pd.to_datetime(df['DateTime'], format="%Y%m%d-%H%M%S")

# # Compute time (in seconds) since start
# df['t_s'] = (df['datetime'] - df['datetime'].iloc[0]).dt.total_seconds()

# # Adjust for video speedup
# speed_factor = 200   # change this if needed
# df['t_video'] = df['t_s'] / speed_factor

# # Choose what you want to show — e.g., Cryo Temperature
# with open("temp_overlay.txt", "w") as f:
#     for _, row in df.iterrows():
#         f.write(f"{row['t_video']:.3f} drawtext reinit text='Cryo {row['Cryo Temperature']:.1f} K'\n")

# print("Wrote temp_overlay.txt")


# .\ffmpeg.exe -i "20251008.mp4" -vf "sendcmd=f=temp_overlay.txt, drawtext=reload=1:fontfile=/Windows/Fonts/arial.ttf:fontsize=36:fontcolor=white:x=20:y=20" -an "20251008_withTemp.mp4"
# .\ffmpeg.exe -i "20251008_600x.mp4" -vf "sendcmd=f=temp_overlay.txt,drawtext=reload=1:fontfile=/Windows/Fonts/arial.ttf:fontsize=36:fontcolor=white:x=20:y=20" -codec:a copy "20251008_withTemp.mp4"

# import pandas as pd

# # Load your CSV (tab or comma delimited)
# df = pd.read_csv(r"C:\Users\JaramilloGroup\Documents\Python\ControlSoftware\logs\CryoTest_20251009-112441.csv", sep=",")


# df['datetime'] = pd.to_datetime(df['DateTime'], format="%Y%m%d-%H%M%S")
# df['t_s'] = (df['datetime'] - df['datetime'].iloc[0]).dt.total_seconds()

# # --- Adjust for video speed ---
# speed_factor = 200  # change to your value
# df['t_video'] = df['t_s'] / speed_factor

# # --- Write FFmpeg command file ---
# with open("temp_overlay.txt", "w", encoding="utf-8") as f:
#     for _, row in df.iterrows():
#         label = f"Cryo {row['Cryo Temperature']:.1f} K"
#         safe_label = label.replace("'", r"\'")  # escape apostrophes if any
#         f.write(f"{row['t_video']:.3f} [enter] drawtext reinit \"text='{safe_label}'\"\n")



#!/usr/bin/env python3
import csv
from datetime import datetime, timedelta
from pathlib import Path

# ==== EDIT THESE FOR YOUR CASE ====
CSV_PATH = Path(r"C:\Users\JaramilloGroup\Documents\Python\ControlSoftware\logs\CryoTest_20251016-084644.csv")  # your CSV file
DATETIME_COL = "DateTime"    # column with format: YYYYMMDD-HHMMSS (e.g., 20251009-112607)
REACTION_T_COL = "Reaction Temperature"
REACTION_P_COL = "Reaction Pressure"

# If your video time t=0 aligns to this data timestamp, set BASE_DATETIME to that value.
# Usually you'll pick the first row's DateTime (recommended).
BASE_DATETIME = None  # e.g., "2025-10-09 11:26:07" or None to auto-use first row

# Your video is already sped up by this factor (e.g., 8 means 8x faster than real-time)
SPEEDUP = 600

# Optional extra shift (seconds) to nudge all overlays forward/back on the video timeline.
VIDEO_OFFSET_S = 0 # (50*60+50)-(46*60+44)

# Text formatting
T_FMT = "{:.1f}"  # temperature formatting
P_FMT = "{:.2f}"  # pressure formatting
LABEL_TEMPLATE = "Reaction T: {T}    Reaction P: {P}"

# ASS styling (position top-left with a subtle border)
ASS_STYLE_NAME = "Overlay"
ASS_FONT = "DejaVu Sans"
ASS_FONTSIZE = 36
ASS_BOLD = 0
ASS_OUTLINE = 2
ASS_SHADOW = 0
ASS_PRIMARY_COLOUR = "&H00FFFFFF"   # white
ASS_OUTLINE_COLOUR = "&H00000000"   # black
ASS_ALIGNMENT = 7  # 7 = top-left, 8 = top-center, 9 = top-right
ASS_MARGIN_L, ASS_MARGIN_R, ASS_MARGIN_V = 40, 40, 40

OUT_ASS = Path("overlay.ass")
# ==================================

def parse_dt(s: str) -> datetime:
    # Input like 20251009-112607
    return datetime.strptime(s, "%Y%m%d-%H%M%S")

def ass_time(t: float) -> str:
    """Seconds -> ASS time 'H:MM:SS.cs' (centiseconds)."""
    if t < 0: t = 0
    td = timedelta(seconds=t)
    total_seconds = int(td.total_seconds())
    cs = int((t - int(t)) * 100 + 1e-6)  # round down to centiseconds
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"

def read_rows(csv_path: Path):
    """Always read a comma-delimited CSV."""
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        rdr = csv.DictReader(f, delimiter=",")
        rows = list(rdr)
    return rows

def main():
    rows = read_rows(CSV_PATH)
    if not rows:
        raise SystemExit("No rows found in CSV.")

    # Parse datetimes and sort just in case
    for r in rows:
        r["_dt"] = parse_dt(r[DATETIME_COL])
    rows.sort(key=lambda r: r["_dt"])

    base_dt = parse_dt(BASE_DATETIME.replace(" ", "").replace(":", "").replace("-", "")) if isinstance(BASE_DATETIME, str) else rows[0]["_dt"]

    # Build (start_video_s, end_video_s, label)
    intervals = []
    for i, r in enumerate(rows):
        start_real_s = (r["_dt"] - base_dt).total_seconds()
        start_vid_s = start_real_s / SPEEDUP + VIDEO_OFFSET_S

        if i < len(rows) - 1:
            next_real_s = (rows[i+1]["_dt"] - base_dt).total_seconds()
            # end at the next sample's start (exclusive)
            end_vid_s = next_real_s / SPEEDUP + VIDEO_OFFSET_S
        else:
            # last entry: give it a small duration (e.g. 2 seconds on video)
            end_vid_s = start_vid_s + 2.0

        # Format label
        try:
            T = float(r[REACTION_T_COL])
        except:
            T = float("nan")
        try:
            P = float(r[REACTION_P_COL])
        except:
            P = float("nan")

        label = LABEL_TEMPLATE.format(T=T_FMT.format(T), P=P_FMT.format(P))
        intervals.append((start_vid_s, end_vid_s, label))

    # Write ASS
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: {ASS_STYLE_NAME},{ASS_FONT},{ASS_FONTSIZE},{ASS_PRIMARY_COLOUR},&H000000FF,{ASS_OUTLINE_COLOUR},&H00000000,{ASS_BOLD},0,0,0,100,100,0,0,1,{ASS_OUTLINE},{ASS_SHADOW},{ASS_ALIGNMENT},{ASS_MARGIN_L},{ASS_MARGIN_R},{ASS_MARGIN_V},0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".rstrip("\n")

    with OUT_ASS.open("w", encoding="utf-8") as f:
        f.write(header + "\n")
        for (s, e, txt) in intervals:
            f.write(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},{ASS_STYLE_NAME},,0,0,0,,{txt}\n")

    print(f"Wrote {OUT_ASS.resolve()} with {len(intervals)} intervals.")

if __name__ == "__main__":
    main()

# ffmpeg -i spedup.mp4 -vf "ass=overlay.ass" -c:a copy out_with_labels.mp4
