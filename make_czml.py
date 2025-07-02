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
        # GISデータの読み込み
        geodata_path = os.path.join(rootFolderath, train["geodata_filename"])

        # 駅リスト（駅名、位置情報）の読み込み
        gdf_station = gpd.read_file(geodata_path, layer = train["station_layername"])
        gdf_station = gdf_station[gdf_station["夜行列車停車駅"]==True]

        # 時刻表情報の読み込み
        timetablepath = os.path.join(rootFolderath, r"timetable",train["timetable_filename"])
        df_time = pd.read_csv(timetablepath, encoding="utf8")
        
        # 列車の軌跡情報の読み込み
        df_trajlist = gpd.read_file(geodata_path, layer = train["trajectory_layername"])
        g = df_trajlist[df_trajlist["name"]==train["trajectory_name"]]
        if len(g) != 1:
            print("  --ERROR: trajectory_nameがないか、同じ軌跡が複数あります。")
            continue
        if len(g.iloc[0].geometry.geoms) != 1:
            print("  --ERROR: １つのジオメトリにポリゴンが複数あります。１つだけにしてください。")
            continue

        # 軌跡をラインからポイントに変換し、距離を追加
        p = g.iloc[0].geometry.geoms[0].coords
        X, Y, Z = [x for x, y, z in p], [y for x, y, z in p], [z for x, y, z in p]
        gdf_traj = gpd.GeoDataFrame({"X" : X, "Y" : Y, "Z" : Z}, geometry=gpd.points_from_xy(X, Y, Z), crs=df_trajlist.crs)
        distance, n, pre_p = 0, 0, (0, 0, 0)
        for index, row in gdf_traj.iterrows():
            if n == 0:
                gdf_traj.at[index, "distance"] = distance
            else:
                distance += pre_p.distance(row["geometry"]) * 1000
                gdf_traj.at[index, "distance"] = distance
            n += 1
            pre_p = row["geometry"]

        # ベースとするCZMLファイルの内容
        czml_base = json.load(open(os.path.join(rootFolderath,"czml_base.json"), encoding="utf-8"))

        # CZMLフォルダのパス
        outputFolderath = os.path.join(rootFolderath, r"czml")

        # タイムゾーン設定
        tzinfo = datetime.timezone(datetime.timedelta(hours=9))
        standard_time = datetime.datetime(1980,4,1,12,00,00, tzinfo=tzinfo)

        # 列車IDの設定
        train_id = os.path.splitext(os.path.basename(timetablepath))[0]

        ## ==============CZMLデータ作成処理==============
        # 列車の移動情報を作成
        txyz, start_time, end_time = getTXYZData(df_time, gdf_traj, gdf_station, standard_time)
        
        if txyz is None:
            continue

        # CZMLデータの内容を作成
        base = getCZMLData(train_id, train["name"], "", txyz, standard_time, end_time, czml_base)
        outputFileath = os.path.join(outputFolderath, "{0}.czml".format(train_id))

        # CZMLファイルの作成
        with open(outputFileath, 'w') as f:
            json.dump(base, f, indent=4)

    print("Complete !")


def getCZMLData(id, name, description, txyz, standard_time, end_time, czml_base):
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

    end_time.days
    for i in range(end_time.days + 1):
        t = standard_time - datetime.timedelta(days=i)
        b = copy.deepcopy(czml_base)
        b["id"] = id + str(i)
        b["name"] = name
        b["description"] = description
        b["availability"] = "{0}/{1}".format(standard_time.isoformat(), (standard_time + datetime.timedelta(days=1)).isoformat())
        b["position"]["cartographicDegrees"] = txyz
        b["position"]["epoch"] = t.isoformat()
        result.append(b)
    return result


def getTXYZData(df_time, gdf_traj, gdf_st, standard_time):
    """列車の時刻、X、Y、Z情報のリストを作成する。

    Args:
        df_time(pandas.DataFrame): 列車の時刻表
        df_traj(pandas.DataFrame): 列車の運行軌跡
        df_st(pandas.DataFrame): 停車駅リスト
        standard_time(date): 基準時間

    Returns:
        list: 列車の時刻、X、Y、Z情報のリスト
        timedelta: 列車の出発時刻
        timedelta: 列車の終着時刻
    """

    # 列車の時刻表を読み込み、standard timeからの秒数、位置情報を取得する
    df_time = df_time.set_index("時刻")
    diff_day = min((pd.to_datetime(df_time.index).tz_localize('Asia/Tokyo') - standard_time).days)
    df_time.index = pd.to_datetime(df_time.index).tz_localize('Asia/Tokyo') - standard_time - datetime.timedelta(days=diff_day)
    start_time, end_time = min(df_time.index), max(df_time.index)

    df_time["秒数"] = df_time.index.total_seconds()
    gdf_time = df_time.merge(gdf_st, left_on = "駅名", right_on = "旧駅名", how = "left")

    # 駅一覧にない駅名が時刻表にないか検査
    if len(gdf_time[gdf_time["geometry"]==None]) > 0:
        print("　　---次の駅名が駅一覧に見つかりませんでした。処理をスキップします。{0}".format(str(list(gdf_time[gdf_time["geometry"]==None]["駅名"]))))
        return None, None, None


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

    return txyz, start_time, end_time


main()