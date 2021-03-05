"""グラフ生成."""

import argparse
import configparser
import datetime
import os
import statistics
import typing as typ
import bokeh.models as bm
import bokeh.plotting as bp
import db_store


def calc_電力量(row) -> float:
    """電力量を計算する.

    Args:
        row: 1件分のデータ

    Returns:
        電力量
    """
    unit: typ.Dict[int, float] = {
        0x00: 1.0,
        0x01: 0.1,
        0x02: 0.01,
        0x03: 0.001,
        0x04: 0.0001,
        0x0A: 10,
        0x0B: 100,
        0x0C: 1000,
        0x0D: 10000,
    }
    係数: int = row["係数"]
    積算電力量: int = row["積算電力量"]
    電力量単位: int = row["電力量単位"]
    単位補正値: float = 1.0

    if 電力量単位 in unit:
        単位補正値 = unit[電力量単位]
    else:
        print(f"電力量単位異常: {電力量単位:X}")
    return 係数 * 積算電力量 * 単位補正値


def make_power_graph(output_file: str, data: typ.List, window: int) -> None:
    """グラフ作成.

    Args:
        output_file: 出力ファイル名
        data: データ
        window: 移動平均のサンプル数
    """
    cols: typ.Tuple = ("time", "電力量", "電力", "電流R", "電流T", "MA電力", "MA電流R", "MA電流T")
    datadict: typ.Dict = {}
    for col in cols:
        datadict[col] = []
    has_data: bool = len(data) > 0
    for row in data:
        datadict["time"].append(row["created_at"])
        datadict["電力量"].append(calc_電力量(row))
        datadict["電力"].append(row["瞬時電力"])
        datadict["電流R"].append(row["瞬時電流_r"] / 10.0)
        datadict["電流T"].append(row["瞬時電流_t"] / 10.0)
        datadict["MA電力"].append(statistics.mean(datadict["電力"][-window:]))
        datadict["MA電流T"].append(statistics.mean(datadict["電流T"][-window:]))
        datadict["MA電流R"].append(statistics.mean(datadict["電流R"][-window:]))

    source: bp.ColumnDataSource = bp.ColumnDataSource(datadict)
    tooltips: typ.List[typ.Tuple[str, str]] = [
        ("time", "@time{%F %T}"),
        ("積算電力量", "@{電力量}{0,0.0}"),
        ("瞬時電力", "@{電力}{0,0}"),
        ("瞬時電流(R相)", "@{電流R}{0,0.0}"),
        ("瞬時電流(T相)", "@{電流T}{0,0.0}"),
    ]
    hover_tool: bm.HoverTool = bm.HoverTool(tooltips=tooltips, formatters={"@time": "datetime"})

    bp.output_file(output_file, title="Power consumption")
    fig: bp.figure = bp.figure(
        title="Power consumption",
        x_axis_type="datetime",
        x_axis_label="時刻",
        y_axis_label="電力量[kWh]",
        sizing_mode="stretch_both",
    )
    fig.add_tools(hover_tool)
    fmt: typ.List[str] = ["%H:%M"]
    fig.xaxis.formatter = bm.DatetimeTickFormatter(hours=fmt, hourmin=fmt, minutes=fmt)
    if has_data:
        電力量_min: float = min(datadict["電力量"])
        電力量_max: float = max(datadict["電力量"])
        電力量_5p: float = (電力量_max - 電力量_min) * 0.05
        fig.y_range = bm.Range1d(電力量_min - 電力量_5p, 電力量_max + 電力量_5p)
    fig.extra_y_ranges["W"] = bm.Range1d(0, max(datadict["電力"]) * 1.05 if has_data else 0)
    fig.add_layout(bm.LinearAxis(y_range_name="W", axis_label="電力[W]"), "left")
    fig.extra_y_ranges["A"] = bm.Range1d(0, max(*datadict["電流R"], *datadict["電流T"]) * 1.05 if has_data else 0)
    fig.add_layout(bm.LinearAxis(y_range_name="A", axis_label="電流[A]"), "right")

    fig.line("time", "電力量", legend_label="積算電力量", line_color="red", source=source)

    raw_data: typ.List = [
        ("電力", "W", "瞬時電力", "orange"),
        ("電流R", "A", "瞬時電流(R相)", "blue"),
        ("電流T", "A", "瞬時電流(T相)", "green"),
    ]
    for col, range_name, legend_label, color in raw_data:
        fig.line(
            "time",
            col,
            y_range_name=range_name,
            legend_label=legend_label,
            line_color=color,
            line_alpha=0.8,
            source=source,
        ).visible = False

    ma_data: typ.List = [
        ("MA電力", "W", "瞬時電力(移動平均)", "orange"),
        ("MA電流R", "A", "瞬時電流(R相)(移動平均)", "blue"),
        ("MA電流T", "A", "瞬時電流(T相)(移動平均)", "green"),
    ]
    for col, range_name, legend_label, color in ma_data:
        fig.line(
            "time",
            col,
            y_range_name=range_name,
            legend_label=legend_label,
            line_color=color,
            line_width=2,
            line_alpha=0.8,
            line_dash="dotted",
            source=source,
        )

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
    parser.add_argument("-w", "--window", type=int, help="window size of moving average", default=30)

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
    output_file: str = f"power_{start_time.date()}.html"
    if args.output:
        if os.path.isdir(args.output):
            output_file = os.path.join(args.output, output_file)
        else:
            output_file = args.output

    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    db_url: str = inifile.get("routeB", "db_url")

    store: db_store.DBStore = db_store.DBStore(db_url)
    data: typ.List = store.select_power_log(start_time, end_time)

    make_power_graph(output_file, data, args.window)
    print(output_file)


if __name__ == "__main__":
    main()
