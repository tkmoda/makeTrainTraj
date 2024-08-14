import json, numpy, glob, os
import pandas as pd
import datetime

station_list_path = r"C:\Users\takumi\Documents\railway_data\station_list2.csv"
time_paths = glob.glob(r"C:\Users\takumi\Documents\railway_data\time_*.csv")

df_station = pd.read_csv(station_list_path)

standard_time = datetime.datetime(1978,10,2,00,00,00)

def getCZML(id, name, description, txyz):
    return [
        {
            "id": "document",
            "name": "name",
            "version": "1.0"
        },
        {
            "id": id,
            "name": name,
            "description": description,
            "availability": "1978-10-03T12:00:00Z/1978-10-04T12:00:00Z",
            "position": {
                "epoch": "1978-10-03T00:00:00Z",
                "cartographicDegrees": txyz
            },
            "billboard": {
                "image": "imageURL.png",
                "scale": 0.3
            },
            "point": {
                "color": {
                    "rgba": [255,255,255,255]
                },
                "pixelSize": 8
            }
        },
        {
            "id": id + "-2",
            "name": name,
            "description": description,
            "availability": "1978-10-03T12:00:00Z/1978-10-04T12:00:00Z",
            "position": {
                "epoch": "1978-10-02T00:00:00Z",
                "cartographicDegrees": txyz
            },
            "billboard": {
                "image": "imageURL.png",
                "scale": 0.3
            },
            "point": {
                "color": {
                    "rgba": [255,255,255,255]
                },
                "pixelSize": 8
            }
        }
    ]


for time_path in time_paths:
    filename = os.path.splitext(os.path.basename(time_path))[0]
    id = filename
    name = filename
    description = ""

    df_time = pd.read_csv(time_path, encoding="utf8")
    df_time["時刻"] = pd.to_datetime(df_time["時刻"])
    df_time["時刻"] = df_time["時刻"] - standard_time
    df_time["秒数"] = df_time["時刻"].dt.total_seconds()

    df_merge = df_time.merge(df_station, left_on = "駅名", right_on = "旧駅名", how = "left")
    df_out = df_merge[["秒数", "X", "Y", "Z"]]

    txyz = []
    for set in df_out.values.tolist():
        txyz.extend(set)

    base = getCZML(id, name, description, txyz)

    with open(r'C:\Users\takumi\Documents\railway_data\{0}.czml'.format(filename), 'w') as f:
        json.dump(base, f, indent=4)


