"""温度グラフ生成."""

import argparse
import configparser
import datetime
import os
import typing as typ
import bokeh.models as bm
import bokeh.plotting as bp
import db_store


def make_temp_graph(output_file: str, data: typ.List) -> None:
    """グラフ作成.

    Args:
        output_file: 出力ファイル名
        data: データ
    """
    cols: typ.Tuple = ("time", "temp")
    datadict: typ.Dict = {}
    for col in cols:
        datadict[col] = []
    for row in data:
        datadict["time"].append(row["created_at"])
        datadict["temp"].append(row["temp"] / 1000)

    source: bp.ColumnDataSource = bp.ColumnDataSource(datadict)
    tooltips: typ.List[typ.Tuple[str, str]] = [
        ("time", "@time{%F %T}"),
        ("temp", "@{temp}"),
    ]
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
    if len(data) > 0:
        ymax: int = int(max(datadict["temp"]) + 10)
        fig.y_range = bm.Range1d(0, ymax)

    fig.line("time", "temp", legend_label="温度", line_color="red", source=source)

    # fig.legend.click_policy = "hide"

    bp.save(fig)


def main() -> None:
    """メイン処理."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("-s", "--start", help="start time")
    parser.add_argument("-e", "--end", help="end time")

    args: argparse.Namespace = parser.parse_args()

    today: datetime.date = datetime.date.today()

    start_time: datetime.datetime = datetime.datetime.combine(today, datetime.time())
    if args.start:
        start_time = datetime.datetime.fromisoformat(args.start)
    end_time: datetime.datetime = start_time + datetime.timedelta(days=1)
    if args.end:
        end_time = datetime.datetime.fromisoformat(args.end)
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
    data: typ.List = store.select_temp_log(start_time, end_time)

    make_temp_graph(output_file, data)
    print(output_file)


if __name__ == "__main__":
    main()
