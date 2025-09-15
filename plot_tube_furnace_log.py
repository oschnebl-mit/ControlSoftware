import pandas as pd 
import matplotlib.pyplot as plt 
import datetime as dt
import matplotlib.dates as mdates


path = r'C:\Users\oschn\MIT Dropbox\Olivia Schneble\jaramillogroupshared\Data\Jaramillo lab\Big tube furnace\log files\2025\20250729_Pb_sulfurization\TubeFurnaceGUI_20250729-135647.csv'
df = pd.read_csv(r'C:\Users\oschn\Dropbox (MIT)\jaramillogroupshared\Data\Jaramillo lab\Big tube furnace\log files\2025\250522_Sn_sulfurization\TubeFurnaceGUI_20250522-164059.csv')

timestamp = df['Timestamp']
time = [dt.datetime.fromtimestamp(ts) for ts in timestamp]

T1 = df['Zone 1 Temperature']
T2 = df['Zone 2 Temperature']
T3 = df['Zone 3 Temperature']

fig,ax1 = plt.subplots(1,1)
ax2 = ax1.twinx()

ax1.plot(time,T1,color='tab:gray')
ax1.plot(time,T2,color='tab:gray')
ax1.plot(time,T3,color='tab:gray')

ax2.plot(time,df['Ar_sccm'],color='tab:green',label="Ar")
ax2.plot(time,df['H2S_sccm'],color='tab:orange',label="H2S")

# plt.xticks(time[0::10])
ax1.tick_params(axis='x',rotation=25)

date_format = mdates.DateFormatter('%Y-%m-%d %H:%M')
ax1.xaxis.set_major_formatter(date_format)

ax1.set_ylabel('Temperature (C)')
ax2.set_ylabel('Flow (sccm)')
plt.legend()

plt.show()
