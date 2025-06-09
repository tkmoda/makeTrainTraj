import json, numpy, glob, os
import pandas as pd
import datetime
import geopandas as gpd
from scipy.spatial import cKDTree


def main():
    rootFolderath = os.path.dirname(__file__)

    settings = json.load(open(os.path.join(rootFolderath,"settings.json")))
    print(settings)
    print(type(settings))

    # settings = [
    #     {
    #         "name" : "はやぶさ（（上り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_hayabusa_up_19781003.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_hayabusa.csv")
    #     },
    #     {
    #         "name" : "はやぶさ（（下り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_hayabusa_down_19781003.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_hayabusa.csv")
    #     },
    #     {
    #         "name" : "さくら（上り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura_up_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura.csv")
    #     },
    #     {
    #         "name" : "さくら（下り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura_down_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura.csv")
    #     },
    #     {
    #         "name" : "さくら（上り：長崎）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura-nagasaki_up_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura-nagasaki.csv")
    #     },
    #     {
    #         "name" : "さくら（下り：長崎）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura-nagasaki_down_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura-nagasaki.csv")
    #     },
    #     {
    #         "name" : "さくら（上り：佐世保）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura-sasebo_up_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura-sasebo.csv")
    #     },
    #     {
    #         "name" : "さくら（下り：佐世保）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_sakura-sasebo_down_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_sakura-sasebo.csv")
    #     },
    #     {
    #         "name" : "富士（上り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_fuji_up_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_fuji.csv")
    #     },
    #     {
    #         "name" : "富士（下り）",
    #         "stationList_path" : os.path.join(rootFolderath, r"stationlist",r"station_list2.csv"),
    #         "timetablepath" : os.path.join(rootFolderath, r"timetable",r"time_fuji_down_19820302.csv"),
    #         "trajectorypath" : os.path.join(rootFolderath, r"trajectory",r"trajectory_fuji.csv")
    #     },
    # ]

    for setting in settings:
        # 駅リスト（駅名、位置情報）のファイルパス
        # stationList_path = setting["stationList_path"]
        stationList_path = os.path.join(rootFolderath, r"stationlist",setting["stationList_filename"])

        # 時刻表情報のファイルパス
        # timetablepath = setting["timetablepath"]
        timetablepath = os.path.join(rootFolderath, r"timetable",setting["timetable_filename"])
        
        # 列車の軌跡情報のファイルパス
        # trajectorypath = setting["trajectorypath"]
        trajectorypath = os.path.join(rootFolderath, r"trajectory",setting["trajectory_filename"])
        

        # CZMLファイルのパス
        outputFolderath = os.path.join(rootFolderath, r"czml")

        standard_time = datetime.datetime(1978,10,2,00,00,00)

        df_time = pd.read_csv(timetablepath, encoding="utf8")
        df_traj = pd.read_csv(trajectorypath, encoding="shift_jis")
        df_station = pd.read_csv(stationList_path)

        filename = os.path.splitext(os.path.basename(timetablepath))[0]

        makeCZML(df_time, df_traj, df_station, outputFolderath, standard_time, filename, filename, "")

def getCZMLData(id, name, description, txyz):
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
            "model": {
                "gltf": "Abstract_train.glb",
                "scale": 10.0,
                "minimumPixelSize": 0.1
            },
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
            "model": {
                "gltf": "Abstract_train.glb",
                "scale": 10.0,
                "minimumPixelSize": 0.1
            },
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


def makeCZML(df_time, df_traj, df_st, outputFolderath, standard_time, id="", name="", description="" ):
    description = ""

    # standard timeからの秒数を計算
    df_time["時刻"] = pd.to_datetime(df_time["時刻"])
    df_time["時刻"] = df_time["時刻"] - standard_time
    df_time["秒数"] = df_time["時刻"].dt.total_seconds()

    df_merge = df_time.merge(df_st, left_on = "駅名", right_on = "旧駅名", how = "left")

    gdf_time = gpd.GeoDataFrame(df_merge, geometry=gpd.points_from_xy(df_merge.X, df_merge.Y, df_merge.Z), crs="EPSG:6668")
    gdf_traj = gpd.GeoDataFrame(df_traj, geometry=gpd.points_from_xy(df_traj.X, df_traj.Y, df_traj.Z), crs="EPSG:6668")

    n_time = numpy.array(list(gdf_time.geometry.apply(lambda x: (x.x, x.y))))
    n_traj = numpy.array(list(gdf_traj.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(n_traj)
    dist, idx = btree.query(n_time, k=1)
    gdf_nearest = gdf_traj.iloc[idx].drop(columns="geometry").reset_index(drop=True)

    ## 時刻表に距離、駅間の平均速度を追記する
    gdf_time2 = pd.concat([
        gdf_time.reset_index(drop=True), 
        gdf_nearest, 
        pd.Series(gdf_nearest["distance"].diff(-1) / gdf_time["秒数"].diff(-1), name="speed"), 
        pd.Series(gdf_nearest["distance"].diff(-1) * -1 , name="diff")
        ], axis=1)
 
    # 駅間の
    l = []
    for i, row in gdf_time2.iterrows():
        print("-------------")
        if row["diff"] == 0:
           gdf_partTraj = gdf_traj[(gdf_traj["distance"] == row["distance"])]
           gdf_partTraj["time"] = row["秒数"]
        #    gdf_partTraj.loc[:,"time"] = row["秒数"]
        else:
            if row["diff"] > 0:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] >= row["distance"]) & (gdf_traj["distance"] < row["distance"] + row["diff"])]
            else:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] <= row["distance"]) & (gdf_traj["distance"] > row["distance"] + row["diff"])]

            gdf_partTraj["time"] = row["秒数"] + (gdf_partTraj["distance"] - row["distance"]) / row["speed"]
            # gdf_partTraj.loc[:,"time"] = row["秒数"] + (gdf_partTraj["distance"] - row["distance"]) / row["speed"]
        l.append(gdf_partTraj)

    gdf_txyz = pd.concat(l)
    # gdf_time2.to_csv(r"C:\Users\takumi\Documents\makeTrainTraj\test.csv", encoding="shift_jis")
    # gdf_txyz.to_csv(r"C:\Users\takumi\Documents\makeTrainTraj\xyz.csv", encoding="shift_jis")


    ## ===================================================
    print("=============")

    # df_out = df_merge[["秒数", "X", "Y", "Z"]]
    df_out = gdf_txyz[["time", "X", "Y", "Z"]]

    txyz = []
    for set in df_out.values.tolist():
        txyz.extend(set)

    base = getCZMLData(id, name, description, txyz)
    outputFileath = os.path.join(outputFolderath, "{0}.czml".format(id))

    with open(outputFileath, 'w') as f:
        json.dump(base, f, indent=4)
    print("Complete !")


main()