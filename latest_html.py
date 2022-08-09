"""最新の状況をhtmlにする."""
import argparse
import configparser
import datetime
import os
import typing as typ
import db_store


def main() -> None:
    """メイン処理."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="output filename")

    args: argparse.Namespace = parser.parse_args()

    output_file: str = "latest.html"
    if args.output:
        if os.path.isdir(args.output):
            output_file = os.path.join(args.output, output_file)
        else:
            output_file = args.output

    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    db_url: str = inifile.get("routeB", "db_url")

    moving_start: datetime.datetime = datetime.datetime.now() - datetime.timedelta(minutes=5)

    store: db_store.DBStore = db_store.DBStore(db_url)
    data: typ.Dict = store.select_latest_log(moving_start)

    with open(output_file, "w", newline="\r\n") as out:
        out.writelines(
            [
                "<!DOCTYPE html>\n",
                "<html lang='ja'>\n",
                "<head>\n",
                "<meta charset='utf-8'/>\n",
                "<meta name='viewport' content='width=device-width, initial-scale=1.0, user-scalable=yes'>\n",
                "<style type='text/css'>\n",
                "body { font-size: x-large; }\n",
                ".red { color: red; }\n",
                ".blue { color: blue; }\n",
                ".green { color: green; }\n",
                ".right { text-align: right; }\n",
                "</style>\n",
                "</head>\n",
                "<body>\n",
                "<table>\n",
            ]
        )
        if data["power"] is not None:
            created_at: str = data["power"]["created_at"].strftime("%Y/%m/%d %H:%M:%S")
            瞬時電力: int = data["power"]["瞬時電力"]
            瞬時電流: float = (data["power"]["瞬時電流_r"] + data["power"]["瞬時電流_t"]) / 10
            平均瞬時電力: typ.Optional[float] = data["power_average"]["瞬時電力"]
            平均瞬時電流: typ.Optional[float] = data["power_average"]["瞬時電流"] / 10
            電流_color: str = ""
            if 瞬時電流 > 28:
                電流_color = "red"
            elif 瞬時電流 > 15:
                電流_color = "blue"
            out.write(f"<tr><td colspan=3>{created_at}</td></tr>\n")
            out.write(f"<tr><td>瞬時電力</td><td class='right'>{瞬時電力}</td><td>[W]</td></tr>\n")
            if 平均瞬時電力 is not None:
                out.write(f"<tr><td>　(平均)</td><td class='right'>{平均瞬時電力:.0f}</td><td>[W]</td></tr>\n")
            out.write(f"<tr><td>瞬時電流</td><td class='right {電流_color}'>{瞬時電流}</td><td>[A]</td></tr>\n")
            if 平均瞬時電流 is not None:
                out.write(f"<tr><td>　(平均)</td><td class='right {電流_color}'>{平均瞬時電流:.1f}</td><td>[A]</td></tr>\n")
        if data["temp"] is not None:
            CPU: float = data["temp"]["temp"] / 1000
            out.write(f"<tr><td>CPU温度</td><td class='right'>{CPU:.1f}</td><td>[℃]</td></tr>\n")
        if data["co2"] is not None:
            CO2: int = data["co2"]["co2"]
            co2_color: str = "blue"
            if CO2 > 2000:
                co2_color = "red"
            elif CO2 > 1000:
                co2_color = "green"
            # temp: int = data["co2"]["temp"]
            out.write(f"<tr><td>CO₂濃度</td><td class='right {co2_color}'>{CO2}</td><td>[ppm]</td></tr>\n")
            # out.write(f"<tr><td>気温</td><td class='right'>{temp}</td><td>[℃]</td></tr>\n")
        if data["bme280"] is not None:
            temp: float = data["bme280"]["temp"]
            hum: float = data["bme280"]["humidity"]
            pres: float = data["bme280"]["pressure"]
            temp_color: str = "green"
            if temp < 18:
                temp_color = "blue"
            elif temp > 25:
                temp_color = "red"
            hum_color: str = "green"
            if hum < 40:
                hum_color = "blue"
            elif hum > 65:
                hum_color = "red"
            out.write(f"<tr><td>気温</td><td class='right {temp_color}'>{temp:.1f}</td><td>[℃]</td></tr>\n")
            out.write(f"<tr><td>湿度</td><td class='right {hum_color}'>{hum:.1f}</td><td>[%]</td></tr>\n")
            out.write(f"<tr><td>気圧</td><td class='right'>{pres:.1f}</td><td>[hPa]</td></tr>\n")
        out.writelines(
            [
                "</table>\n" "</body>\n",
                "</html>\n",
            ]
        )


if __name__ == "__main__":
    main()
