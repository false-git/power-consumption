"""スマートメーターから電力消費量を読むよ."""

import argparse
import configparser
import sys
import skcommand


def main() -> None:
    """メイン処理."""
    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    device: str = inifile.get("routeB", "device")
    # id: str = inifile.get("routeB", "id")
    # password: str = inifile.get("routeB", "password")
    # db_url: str = inifile.get("routeB", "db_url")

    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-i", "--info", action="store_true", help="send SKINFO command")
    parser.add_argument("-r", "--reg", help="send SKREG command with register S<REG>")
    parser.add_argument("-v", "--value", help="SKREG command with VALUE")

    args: argparse.Namespace = parser.parse_args()

    sk: skcommand.SKSerial = skcommand.SKSerial(device)
    if args.info:
        print(sk.skinfo())
        sys.exit(0)
    if args.reg is not None:
        reg: int = int(args.reg, 16)
        if reg < 0 or reg > 255:
            parser.error("REG is not in [0, ff]")
            sys.exit(1)
        print(sk.sksreg(reg, args.value))


if __name__ == "__main__":
    main()
