"""スマートメーターから電力消費量を読むよ."""

import argparse
import configparser
import re
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

        connection_params: typ.Optional[typ.Dict[str, str]] = self.scan()
        if connection_params is None:
            sys.exit(1)
        if not self.join(connection_params):
            # TODO: リトライとかをどうするか要検討
            sys.exit(1)

    def scan(self) -> typ.Optional[typ.Dict[str, str]]:
        """SKSCANでスマートメーターを探し、接続パラメータを取得.

        Returns:
            成功したときはパラメータのdict、失敗したらNone
        """
        params: typ.Dict[str, str] = self.sk.scan_pan()
        if len(params) == 0:
            print("スマートメーターが見つかりませんでした。")
            return None
        addr: str = params["Addr"]
        ipv6addr: str = self.sk.skll64(addr)
        if re.match(r"([0-9A-F]{4}:){7}[0-9A-F]{4}", ipv6addr):
            print(f"スマートメーターのIPv6アドレスの取得に失敗しました。 [{ipv6addr}]")
            return None
        params["IPv6Addr"] = ipv6addr
        return params

    def join(self, params: typ.Dict[str, str]) -> bool:
        """PANA接続シーケンス.

        Args:
            params: 接続パラメータ

        Returns:
            成功したらTrue
        """
        channel: str = params["Channel"]
        pan_id: str = params["Pan ID"]
        ipv6addr: str = params["IPv6Addr"]
        if self.sk.sksreg(0x2, channel) is None:
            print("チャンネルの設定に失敗しました。")
            return False
        if self.sk.sksreg(0x3, pan_id) is None:
            print("チャンネルの設定に失敗しました。")
            return False
        if not self.sk.skjoin(ipv6addr):
            print("PANA接続シーケンスに失敗しました。")
            return False
        return True


if __name__ == "__main__":
    pc: PowerConsumption = PowerConsumption()
    pc.main()
