import json, numpy, glob, os
import pandas as pd
import datetime
import geopandas as gpd
from scipy.spatial import cKDTree


def main():
    rootFolderath = os.path.dirname(__file__)

    settings = json.load(open(os.path.join(rootFolderath,"settings.json"), encoding="utf-8"))
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
        
        czml_base = json.load(open(os.path.join(rootFolderath,"czml_base.json"), encoding="utf-8"))

        # CZMLファイルのパス
        outputFolderath = os.path.join(rootFolderath, r"czml")

        # tzinfo = datetime.timezone.utc
        tzinfo = datetime.timezone(datetime.timedelta(hours=9))
        standard_time = datetime.datetime(1978,10,2,00,00,00, tzinfo=tzinfo)

        df_time = pd.read_csv(timetablepath, encoding="utf8")
        df_traj = pd.read_csv(trajectorypath, encoding="shift_jis")
        df_station = pd.read_csv(stationList_path)

        filename = os.path.splitext(os.path.basename(timetablepath))[0]

        makeCZML(df_time, df_traj, df_station, outputFolderath, standard_time, id=filename, name=setting["name"], description="", czml_base=czml_base)
    print("Complete !")


def getCZMLData(id, name, description, txyz, standard_time, czml_base):
    meta = {"id": "document",
            "name": "name",
            "version": "1.0"}
    result = [meta]
    for i in range(2):
        t = standard_time + datetime.timedelta(days=i)
        b = czml_base
        b["id"] = id
        b["name"] = name
        b["description"] = description
        b["position"]["cartographicDegrees"] = txyz
        b["position"]["epoch"] = t.isoformat()
        result.append(b)
    return result



def makeCZML(df_time, df_traj, df_st, outputFolderath, standard_time, czml_base, id="", name="", description=""):
    description = ""

    # standard timeからの秒数を計算
    df_time = df_time.set_index("時刻")
    df_time.index = pd.to_datetime(df_time.index).tz_localize('Asia/Tokyo') - standard_time
    df_time["秒数"] = df_time.index.total_seconds()

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
        if row["diff"] == 0:
            gdf_partTraj = gdf_traj[(gdf_traj["distance"] == row["distance"])].copy()
            gdf_partTraj["time"] = row["秒数"]
        else:
            if row["diff"] > 0:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] >= row["distance"]) & (gdf_traj["distance"] < row["distance"] + row["diff"])].copy()
            else:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] <= row["distance"]) & (gdf_traj["distance"] > row["distance"] + row["diff"])].copy()

            gdf_partTraj["time"] = row["秒数"] + (gdf_partTraj["distance"] - row["distance"]) / row["speed"]
            # gdf_partTraj.loc[:,"time"] = row["秒数"] + (gdf_partTraj["distance"] - row["distance"]) / row["speed"]
        l.append(gdf_partTraj)

    gdf_txyz = pd.concat(l)
    # gdf_time2.to_csv(r"C:\Users\takumi\Documents\makeTrainTraj\test.csv", encoding="shift_jis")
    # gdf_txyz.to_csv(r"C:\Users\takumi\Documents\makeTrainTraj\xyz.csv", encoding="shift_jis")


    ## ===================================================

    # df_out = df_merge[["秒数", "X", "Y", "Z"]]
    df_out = gdf_txyz[["time", "X", "Y", "Z"]]

    txyz = []
    for set in df_out.values.tolist():
        txyz.extend(set)

    base = getCZMLData(id, name, description, txyz, standard_time, czml_base=czml_base)
    outputFileath = os.path.join(outputFolderath, "{0}.czml".format(id))

    with open(outputFileath, 'w') as f:
        json.dump(base, f, indent=4)


main()