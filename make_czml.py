import json, numpy, glob, os
import pandas as pd
import datetime
import geopandas as gpd
from scipy.spatial import cKDTree
import copy

def main():
    rootFolderath = os.path.dirname(__file__)

    trains = json.load(open(os.path.join(rootFolderath,"settings.json"), encoding="utf-8"))
    for train in trains:
        print("{0}の処理を開始します。".format(train["name"]))
        ## ==============初期設定==============
        # 駅リスト（駅名、位置情報）の読み込み
        # stationList_path = os.path.join(rootFolderath, r"stationlist",train["stationList_filename"])
        # df_station = pd.read_csv(stationList_path)

        geodata_path = os.path.join(rootFolderath, train["geodata_filename"])
        df_station = gpd.read_file(geodata_path, layer = train["station_layername"])
        df_station = df_station[df_station["夜行列車停車駅"]==True]


        # 時刻表情報の読み込み
        timetablepath = os.path.join(rootFolderath, r"timetable",train["timetable_filename"])
        df_time = pd.read_csv(timetablepath, encoding="utf8")
        
        # 列車の軌跡情報の読み込み
        trajectorypath = os.path.join(rootFolderath, r"trajectory",train["trajectory_filename"])
        df_traj = pd.read_csv(trajectorypath, encoding="shift_jis")
        
        # ベースとするCZMLファイルの内容
        czml_base = json.load(open(os.path.join(rootFolderath,"czml_base.json"), encoding="utf-8"))

        # CZMLフォルダのパス
        outputFolderath = os.path.join(rootFolderath, r"czml")

        # タイムゾーン設定
        tzinfo = datetime.timezone(datetime.timedelta(hours=9))
        standard_time = datetime.datetime(1978,10,2,00,00,00, tzinfo=tzinfo)

        # 列車IDの設定
        train_id = os.path.splitext(os.path.basename(timetablepath))[0]

        # 列車の移動情報を作成
        txyz = getTXYZData(df_time, df_traj, df_station, standard_time)

        # CZMLデータの内容を作成
        base = getCZMLData(train_id, train["name"], "", txyz, standard_time, czml_base)
        outputFileath = os.path.join(outputFolderath, "{0}.czml".format(train_id))

        # CZMLファイルの作成
        with open(outputFileath, 'w') as f:
            json.dump(base, f, indent=4)

    print("Complete !")


def getCZMLData(id, name, description, txyz, standard_time, czml_base):
    """CZMLデータを生成する。

    Args:
        id(str): 列車のID
        name(str): 列車名
        description(str): 列車の説明
        txyz(list): 列車の軌跡をTXYZ形式で記述
        standard_time(date): 基準時間
        czml_base(obj): ベースとなるCZMLファイルの内容 

    Returns:
        list: CZMLファイルのJSON構造を持ったリスト型
    """
    meta = {"id": "document",
            "name": "name",
            "version": "1.0"}
    result = [meta]
    for i in range(2):
        t = standard_time + datetime.timedelta(days=i)
        b = copy.deepcopy(czml_base)
        b["id"] = id + str(i)
        b["name"] = name
        b["description"] = description
        b["position"]["cartographicDegrees"] = txyz
        b["position"]["epoch"] = t.isoformat()
        result.append(b)
    return result


def getTXYZData(df_time, df_traj, df_st, standard_time):
    """列車の時刻、X、Y、Z情報のリストを作成する。

    Args:
        df_time(pandas.DataFrame): 列車の時刻表
        df_traj(pandas.DataFrame): 列車の運行軌跡
        df_st(pandas.DataFrame): 停車駅リスト
        standard_time(date): 基準時間

    Returns:
        list: 列車の時刻、X、Y、Z情報のリスト
    """

    # 列車の時刻表を読み込み、standard timeからの秒数、位置情報を取得する
    df_time = df_time.set_index("時刻")
    df_time.index = pd.to_datetime(df_time.index).tz_localize('Asia/Tokyo') - standard_time
    df_time["秒数"] = df_time.index.total_seconds()
    gdf_time = df_time.merge(df_st, left_on = "駅名", right_on = "旧駅名", how = "left")

    # 列車の運行軌跡を読み込み、位置情報を取得する
    gdf_traj = gpd.GeoDataFrame(df_traj, geometry=gpd.points_from_xy(df_traj.X, df_traj.Y, df_traj.Z), crs="EPSG:6668")

    # 時刻表の各駅に最も近い運行軌跡のノードを探索する
    n_time = numpy.array(list(gdf_time.geometry.apply(lambda x: (x.x, x.y))))
    n_traj = numpy.array(list(gdf_traj.geometry.apply(lambda x: (x.x, x.y))))
    btree = cKDTree(n_traj)
    dist, idx = btree.query(n_time, k=1)
    gdf_nearest = gdf_traj.iloc[idx].drop(columns="geometry").reset_index(drop=True)

    ## 運行軌跡ノードの累積距離から、時刻表に距離、駅間の平均速度を追記する
    gdf_time2 = pd.concat([
        gdf_time.reset_index(drop=True), 
        gdf_nearest, 
        pd.Series(gdf_nearest["distance"].diff(-1) / gdf_time["秒数"].diff(-1), name="speed"), 
        pd.Series(gdf_nearest["distance"].diff(-1) * -1 , name="diff")
        ], axis=1)
 
    # 駅間の平均速度から、運行軌跡の各ノードごとに通過時刻（秒数）を求める。
    l = []
    for i, row in gdf_time2.iterrows():
        # 停車している場合
        if row["diff"] == 0:
            gdf_partTraj = gdf_traj[(gdf_traj["distance"] == row["distance"])].copy()
            gdf_partTraj["time"] = row["秒数"]
        else:
            # 列車の方向と運行軌跡の方向が同じ場合
            if row["diff"] > 0:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] >= row["distance"]) & (gdf_traj["distance"] < row["distance"] + row["diff"])].copy()
            # 列車の方向と運行軌跡の方向が逆の場合
            else:
                gdf_partTraj = gdf_traj[(gdf_traj["distance"] <= row["distance"]) & (gdf_traj["distance"] > row["distance"] + row["diff"])].copy()

            gdf_partTraj["time"] = row["秒数"] + (gdf_partTraj["distance"] - row["distance"]) / row["speed"]
        l.append(gdf_partTraj)

    gdf_txyz = pd.concat(l)
    df_out = gdf_txyz[["time", "X", "Y", "Z"]]

    txyz = []
    for set in df_out.values.tolist():
        txyz.extend(set)

    return txyz

main()