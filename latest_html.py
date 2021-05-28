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

    output_file: str = f"latest.html"
    if args.output:
        if os.path.isdir(args.output):
            output_file = os.path.join(args.output, output_file)
        else:
            output_file = args.output

    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    db_url: str = inifile.get("routeB", "db_url")

    store: db_store.DBStore = db_store.DBStore(db_url)
    data: typ.Dict = store.select_latest_log()

    with open(output_file, "w", newline="\r\n") as out:
        out.writelines([
            "<!DOCTYPE html>\n",
            "<html lang='ja'>\n",
            "<head>\n",
            "<meta charset='utf-8'/>\n",
            "</head>\n",
            "<body>\n",
            "<table>\n"
        ])
        if data["power"] is not None:
            created_at: str = data["power"]["created_at"].strftime("%Y/%m/%d %H:%M:%S")
            瞬時電力: int = data["power"]["瞬時電力"]
            瞬時電流_r: float = data["power"]["瞬時電流_r"] / 10
            瞬時電流_t: float = data["power"]["瞬時電流_t"] / 10
            out.write(f"<tr><td colspan=3>{created_at}</td></tr>\n")
            out.write(f"<tr><td>瞬時電力</td><td style='text-align: right;'>{瞬時電力}</td><td>[W]</td></tr>\n")
            out.write(f"<tr><td>瞬時電流(R相)</td><td style='text-align: right;'>{瞬時電流_r}</td><td>[A]</td></tr>\n")
            out.write(f"<tr><td>瞬時電流(T相)</td><td style='text-align: right;'>{瞬時電流_t}</td><td>[A]</td></tr>\n")
        if data["temp"] is not None:
            CPU: float = data["temp"]["temp"] / 1000
            out.write(f"<tr><td>CPU温度</td><td style='text-align: right;'>{CPU:.1f}</td><td>[℃]</td></tr>\n")
        if data["co2"] is not None:
            CO2: int = data["co2"]["co2"]
            #temp: int = data["co2"]["temp"]
            out.write(f"<tr><td>CO₂濃度</td><td style='text-align: right;'>{CO2}</td><td>[ppm]</td></tr>\n")
            #out.write(f"<tr><td>気温</td><td style='text-align: right;'>{temp}</td><td>[℃]</td></tr>\n")
        if data["bme280"] is not None:
            temp: float = data["bme280"]["temp"]
            hum: float = data["bme280"]["humidity"]
            pres: float = data["bme280"]["pressure"]
            out.write(f"<tr><td>気温</td><td style='text-align: right;'>{temp:.1f}</td><td>[℃]</td></tr>\n")
            out.write(f"<tr><td>湿度</td><td style='text-align: right;'>{hum:.1f}</td><td>[%]</td></tr>\n")
            out.write(f"<tr><td>気圧</td><td style='text-align: right;'>{pres:.1f}</td><td>[hPa]</td></tr>\n")
        out.writelines([
            "</table>\n"
            "</body>\n",
            "</html>\n",
        ])

if __name__ == "__main__":
    main()
