"""温度グラフ生成."""
import argparse
import configparser
import datetime
import os
import typing as typ
import bokeh.models as bm
import bokeh.plotting as bp
import pandas as pd
import db_store


def make_temp_graph(output_file: str, temp_data: typ.List, co2_data: typ.List) -> None:
    """グラフ作成.

    Args:
        output_file: 出力ファイル名
        temp_data: 温度データ
        co2_data: CO2データ
    """
    tooltips: typ.List[typ.Tuple[str, str]] = [
        ("time", "@time{%F %T}"),
    ]
    df: pd.DataFrame
    deg_max: int = 0
    if len(temp_data) > 0:
        df1: pd.DataFrame = pd.DataFrame(temp_data, columns=list(temp_data[0].keys()))
        df1 = df1.rename(columns={"created_at": "time"})
        if len(co2_data) > 0:
            df1["time"] = df1["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df1["temp"] /= 1000
        df1 = df1[["time", "temp"]].drop_duplicates(subset="time")
        df = df1
        tooltips.append(("CPU温度", "@{temp}"))
        deg_max = int(df["temp"].max()) + 10
    if len(co2_data) > 0:
        df2: pd.DataFrame = pd.DataFrame(co2_data, columns=list(co2_data[0].keys()))
        df2 = df2.rename(columns={"temp": "temp2", "created_at": "time"})
        if len(temp_data) > 0:
            df2["time"] = df2["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df2 = df2[["time", "co2", "temp2", "pressure", "ss"]].drop_duplicates(subset="time")
        df = df2
        tooltips.append(("気温", "@{temp2}"))
        tooltips.append(("CO₂", "@{co2}"))
        deg_max = max(deg_max, int(df["temp2"].max()) + 10)
    if len(temp_data) > 0 and len(co2_data) > 0:
        df = pd.merge(df1, df2, on="time", how="outer")

    source: bp.ColumnDataSource = bp.ColumnDataSource(df)
    hover_tool: bm.HoverTool = bm.HoverTool(tooltips=tooltips, formatters={"@time": "datetime"})

    bp.output_file(output_file, title="Temperature")
    fig: bp.figure = bp.figure(
        title="Temperature",
        x_axis_type="datetime",
        x_axis_label="時刻",
        y_axis_label="温度[℃]",
        sizing_mode="stretch_both",
    )
    fig.add_tools(hover_tool)
    fmt: typ.List[str] = ["%H:%M"]
    fig.xaxis.formatter = bm.DatetimeTickFormatter(hours=fmt, hourmin=fmt, minutes=fmt)
    fig.y_range = bm.Range1d(0, deg_max)
    if len(temp_data) > 0:
        fig.line("time", "temp", legend_label="CPU温度", line_color="red", source=source)
    if len(co2_data) > 0:
        fig.line("time", "temp2", legend_label="気温", line_color="orange", source=source)
        fig.extra_y_ranges = {"ppm": bm.Range1d(0, df["co2"].max() * 1.05)}
        fig.add_layout(bm.LinearAxis(y_range_name="ppm", axis_label="濃度[ppm]"), "right")
        fig.line("time", "co2", legend_label="CO₂", line_color="green", y_range_name="ppm", source=source)

    # fig.legend.click_policy = "hide"

    bp.save(fig)


def main() -> None:
    """メイン処理."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("-s", "--start", help="start time")
    parser.add_argument("-e", "--end", help="end time")
    parser.add_argument("-d", "--days", type=int, help="before n days")

    args: argparse.Namespace = parser.parse_args()

    today: datetime.date = datetime.date.today()

    start_time: datetime.datetime = datetime.datetime.combine(today, datetime.time())
    if args.start:
        start_time = datetime.datetime.fromisoformat(args.start)
    end_time: datetime.datetime = start_time + datetime.timedelta(days=1)
    if args.end:
        end_time = datetime.datetime.fromisoformat(args.end)
    if args.days:
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(args.days)
    output_file: str = f"temp_{start_time.date()}.html"
    if args.output:
        if os.path.isdir(args.output):
            output_file = os.path.join(args.output, output_file)
        else:
            output_file = args.output

    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    db_url: str = inifile.get("routeB", "db_url")

    store: db_store.DBStore = db_store.DBStore(db_url)
    temp_data: typ.List = store.select_temp_log(start_time, end_time)
    co2_data: typ.List = store.select_co2_log(start_time, end_time)

    if len(temp_data) > 0 or len(co2_data) > 0:
        make_temp_graph(output_file, temp_data, co2_data)
        print(output_file)
    else:
        print("no data")


if __name__ == "__main__":
    main()
