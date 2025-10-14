import pandas as pd

# Load your CSV file
df = pd.read_csv("reaction_data.csv", sep="\t")

# Convert DateTime strings to pandas Timestamps
df['datetime'] = pd.to_datetime(df['DateTime'], format="%Y%m%d-%H%M%S")

# Compute time (in seconds) since start
df['t_s'] = (df['datetime'] - df['datetime'].iloc[0]).dt.total_seconds()

# Adjust for video speedup
speed_factor = 200   # change this if needed
df['t_video'] = df['t_s'] / speed_factor

# Choose what you want to show — e.g., Cryo Temperature
with open("temp_overlay.txt", "w") as f:
    for _, row in df.iterrows():
        f.write(f"{row['t_video']:.3f} drawtext reinit text='Cryo {row['Cryo Temperature']:.1f} K'\n")

print("Wrote temp_overlay.txt")


# .\ffmpeg.exe -i "20251008.mp4" -vf "sendcmd=f=temp_overlay.txt, drawtext=reload=1:fontfile=/Windows/Fonts/arial.ttf:fontsize=36:fontcolor=white:x=20:y=20" -an "20251008_withTemp.mp4"
# .\ffmpeg.exe -i "20251008_600x.mp4" -vf "sendcmd=f=temp_overlay.txt,drawtext=reload=1:fontfile=/Windows/Fonts/arial.ttf:fontsize=36:fontcolor=white:x=20:y=20" -codec:a copy "20251008_withTemp.mp4"

