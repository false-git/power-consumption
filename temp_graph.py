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


def make_temp_graph(
    output_file: str, temp_data: typ.List, co2_data: typ.List, bme280_data: typ.List, tsl2572_data: typ.List
) -> None:
    """グラフ作成.

    Args:
        output_file: 出力ファイル名
        temp_data: 温度データ
        co2_data: CO2データ
        bme280_data: BME280のデータ
        tsl2572_data: TSL2572のデータ
    """
    tooltips: typ.List[typ.Tuple[str, str]] = [
        ("time", "@time{%F %T}"),
    ]
    df: pd.DataFrame
    deg_max: int = 0
    num_data: int = 0
    y_axis_label: str = "温度[℃]"
    if len(temp_data) > 0:
        num_data += 1
    if len(co2_data) > 0:
        num_data += 1
    if len(bme280_data) > 0:
        num_data += 1
    if len(temp_data) > 0:
        df1: pd.DataFrame = pd.DataFrame(temp_data, columns=list(temp_data[0].keys()))
        df1 = df1.rename(columns={"created_at": "time"})
        if num_data > 1:
            df1["time"] = df1["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df1["temp"] /= 1000
        df1 = df1[["time", "temp"]].drop_duplicates(subset="time")
        df = df1
        tooltips.append(("CPU温度", "@temp{0.0}"))
        deg_max = int(df["temp"].max()) + 10
    if len(co2_data) > 0:
        df2: pd.DataFrame = pd.DataFrame(co2_data, columns=list(co2_data[0].keys()))
        df2 = df2.rename(columns={"temp": "temp2", "created_at": "time"})
        if num_data > 1:
            df2["time"] = df2["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df2 = df2[["time", "co2", "temp2"]].drop_duplicates(subset="time")
        if len(temp_data) > 0:
            df = pd.merge(df1, df2, on="time", how="outer").sort_values("time")
        else:
            df = df2
        if len(bme280_data) == 0:
            tooltips.append(("気温", "@temp2"))
        tooltips.append(("CO₂", "@co2"))
        deg_max = max(deg_max, int(df["temp2"].max()) + 10)
    if len(bme280_data) > 0:
        df3: pd.DataFrame = pd.DataFrame(bme280_data, columns=list(bme280_data[0].keys()))
        df3 = df3.rename(columns={"temp": "temp3", "created_at": "time"})
        if num_data > 1:
            df3["time"] = df3["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df3 = df3[["time", "temp3", "pressure", "humidity"]].drop_duplicates(subset="time")
        if num_data > 1:
            df = pd.merge(df, df3, on="time", how="outer").sort_values("time")
        else:
            df = df3
        tooltips.append(("気温", "@temp3{0.0}"))
        tooltips.append(("湿度", "@humidity{0.0}"))
        tooltips.append(("気圧", "@pressure{0,0.0}"))
        deg_max = max(deg_max, int(df["temp3"].max()) + 10, int(df["humidity"].max()) + 10)
        y_axis_label += "/湿度[%]"
    if len(tsl2572_data) > 0:
        df4: pd.DataFrame = pd.DataFrame(tsl2572_data, columns=list(tsl2572_data[0].keys()))
        df4 = df4.rename(columns={"created_at": "time"})
        if num_data > 1:
            df4["time"] = df4["time"].apply(lambda x: x.replace(second=0, microsecond=0))
        df4 = df4[["time", "illuminance"]].drop_duplicates(subset="time")
        if num_data > 1:
            df = pd.merge(df, df4, on="time", how="outer").sort_values("time")
        else:
            df = df4
        tooltips.append(("照度", "@illuminance{0.0}"))
        deg_max = max(deg_max, int(df["illuminance"].max()) + 10)
        y_axis_label += "/照度[lx]"

    source: bp.ColumnDataSource = bp.ColumnDataSource(df)
    hover_tool: bm.HoverTool = bm.HoverTool(tooltips=tooltips, formatters={"@time": "datetime"})

    bp.output_file(output_file, title="Temperature")
    fig: bp.figure = bp.figure(
        title="Temperature",
        x_axis_type="datetime",
        x_axis_label="時刻",
        y_axis_label=y_axis_label,
        sizing_mode="stretch_both",
    )
    fig.add_tools(hover_tool)
    fmt: typ.List[str] = ["%H:%M"]
    fig.xaxis.formatter = bm.DatetimeTickFormatter(hours=fmt, hourmin=fmt, minutes=fmt)
    fig.y_range = bm.Range1d(0, deg_max)
    if len(temp_data) > 0:
        fig.line("time", "temp", legend_label="CPU温度", line_color="red", source=source)
    if len(co2_data) > 0:
        if len(bme280_data) == 0:
            fig.line("time", "temp2", legend_label="気温", line_color="darkorange", source=source)
        fig.extra_y_ranges["ppm"] = bm.Range1d(0, max(2000, df["co2"].max() * 1.05))
        fig.add_layout(bm.LinearAxis(y_range_name="ppm", axis_label="濃度[ppm]"), "right")
        fig.line("time", "co2", legend_label="CO₂", line_color="green", y_range_name="ppm", source=source)
    if len(bme280_data) > 0:
        fig.line("time", "temp3", legend_label="気温", line_color="darkorange", source=source)
        fig.line("time", "humidity", legend_label="湿度", line_color="blue", source=source)
        fig.extra_y_ranges["pressure"] = bm.Range1d(min(990, df["pressure"].min()), max(1020, df["pressure"].max()))
        fig.add_layout(bm.LinearAxis(y_range_name="pressure", axis_label="気圧[hPa]"), "right")
        fig.line("time", "pressure", legend_label="気圧", line_color="deeppink", y_range_name="pressure", source=source)
    if len(tsl2572_data) > 0:
        fig.line("time", "illuminance", legend_label="照度", line_color="gold", source=source)

    fig.legend.click_policy = "hide"
    fig.legend.location = "top_left"

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
    bme280_data: typ.List = store.select_bme280_log(start_time, end_time)
    tsl2572_data: typ.List = store.select_tsl2572_log(start_time, end_time)

    if len(temp_data) > 0 or len(co2_data) > 0 or len(bme280_data) > 0 or len(tsl2572_data) > 0:
        make_temp_graph(output_file, temp_data, co2_data, bme280_data, tsl2572_data)
        print(output_file)
    else:
        print("no data")


if __name__ == "__main__":
    main()
