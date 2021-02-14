"""スマートメーターから電力消費量を読むよ."""

import argparse
import configparser
import sys
import typing as typ
import skcommand


class PowerConsumption:
    """スマートメーターから電力消費量を読むクラス."""

    def __init__(self) -> None:
        """初期化."""
        inifile: configparser.ConfigParser = configparser.ConfigParser()
        inifile.read("power_consumption.ini", "utf-8")
        device: str = inifile.get("routeB", "device")
        debug: bool = inifile.getboolean("routeB", "debug", fallback=False)
        self.routeB_id: str = inifile.get("routeB", "id")
        self.routeB_password: str = inifile.get("routeB", "password")
        # db_url: str = inifile.get("routeB", "db_url")

        self.sk: skcommand.SKSerial = skcommand.SKSerial(device, debug)

    def main(self) -> None:
        """メイン処理."""
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        parser.add_argument("-i", "--info", action="store_true", help="send SKINFO command")
        parser.add_argument("-r", "--reg", help="send SKREG command with register S<REG>")
        parser.add_argument("-v", "--value", help="SKREG command with VALUE")

        args: argparse.Namespace = parser.parse_args()

        if args.info:
            print(self.sk.skinfo())
            sys.exit(0)
        if args.reg is not None:
            reg: int = int(args.reg, 16)
            if reg < 0 or reg > 255:
                parser.error("REG is not in [0, ff]")
                sys.exit(1)
            print(self.sk.sksreg(reg, args.value))
            sys.exit(0)

        if not self.sk.routeB_auth(self.routeB_id, self.routeB_password):
            print("ルートBの認証情報の設定に失敗しました。")
            sys.exit(1)

        connection_info: typ.Dict[str, str] = self.sk.scan_pan()
        print(connection_info)

    def scan(self) -> None:
        """SKSCANでスマートメーターを探す."""
        pass


if __name__ == "__main__":
    pc: PowerConsumption = PowerConsumption()
    pc.main()
