"""スマートメーターから電力消費量を読むよ."""

import argparse
import configparser
import re
import struct
import sys
import time
import typing as typ
import db_store
import echonet
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
        self.db_url: str = inifile.get("routeB", "db_url")

        self.sk: skcommand.SKSerial = skcommand.SKSerial(device, debug)

        self.connected: bool = False
        self.temp_flag: bool = False

    def main(self) -> None:
        """メイン処理."""
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        parser.add_argument("-i", "--info", action="store_true", help="send SKINFO command")
        parser.add_argument("-r", "--reg", help="send SKREG command with register S<REG>")
        parser.add_argument("-v", "--value", help="SKREG command with VALUE")
        parser.add_argument("-t", "--temp", action="store_true", help="log Raspberry pi temp")

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

        self.temp_flag = args.temp

        if not self.sk.routeB_auth(self.routeB_id, self.routeB_password):
            print("ルートBの認証情報の設定に失敗しました。")
        elif not self.scan():
            pass
        elif not self.join():
            # TODO: リトライとかをどうするか要検討
            pass
        else:
            self.connected = True

        if not self.temp_flag and not self.connected:
            sys.exit(1)

        self.task()

    def scan(self) -> bool:
        """SKSCANでスマートメーターを探し、接続パラメータを取得.

        Returns:
            成功したときはパラメータをselfに設定し、Trueを返す。
        """
        params: typ.Dict[str, str] = self.sk.scan_pan()
        if len(params) == 0:
            print("スマートメーターが見つかりませんでした。")
            return False
        channel: str = params["Channel"]
        channel_page: str = params.get("Channel Page", "0")
        pan_id: str = params["Pan ID"]
        addr: str = params["Addr"]
        lqi: str = params.get("LQI", "0")
        pair_id: str = params.get("PairID", "")

        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.scan_log(int(channel, 16), int(channel_page, 16), int(pan_id, 16), addr, int(lqi, 16), pair_id)
        del store

        ipv6addr: str = self.sk.skll64(addr)
        if re.match(r"([0-9A-F]{4}:){7}[0-9A-F]{4}", ipv6addr):
            print(f"スマートメーターのIPv6アドレスの取得に失敗しました。 [{ipv6addr}]")
            return False
        # 接続パラメータをselfに保存する。
        self.channel = channel
        self.pan_id = pan_id
        self.ipv6addr = ipv6addr
        return True

    def join(self) -> bool:
        """PANA接続シーケンス.

        Returns:
            成功したらTrue
        """
        if self.sk.sksreg(0x2, self.channel) is None:
            print("チャンネルの設定に失敗しました。")
            return False
        if self.sk.sksreg(0x3, self.pan_id) is None:
            print("チャンネルの設定に失敗しました。")
            return False
        if not self.sk.skjoin(self.ipv6addr):
            print("PANA接続シーケンスに失敗しました。")
            return False
        return True

    def get_prop(self) -> bool:
        """property値読み出し.

        Returns:
            成功したときTrue
        """
        epc_list: typ.List[int] = [
            echonet.EPC_係数,
            echonet.EPC_積算電力量計測値,
            echonet.EPC_積算電力量単位,
            echonet.EPC_瞬時電力計測値,
            echonet.EPC_瞬時電流計測値,
        ]
        props: typ.Optional[typ.List] = self.sk.get_prop(
            self.ipv6addr,
            epc_list,
        )
        if props is None:
            return False

        propdict: typ.Dict[int, bytes] = {}
        for p in props:
            propdict[p.epc] = p.edt

        係数: typ.Optional[int] = None
        積算電力量: typ.Optional[int] = None
        電力量単位: typ.Optional[int] = None
        瞬時電力: typ.Optional[int] = None
        瞬時電流_R: typ.Optional[int] = None
        瞬時電流_T: typ.Optional[int] = None
        if echonet.EPC_係数 in propdict:
            係数 = struct.unpack_from("!L", propdict[echonet.EPC_係数])[0]
        if echonet.EPC_積算電力量計測値 in propdict:
            積算電力量 = struct.unpack_from("!L", propdict[echonet.EPC_積算電力量計測値])[0]
        if echonet.EPC_積算電力量単位 in propdict:
            電力量単位 = struct.unpack_from("B", propdict[echonet.EPC_積算電力量単位])[0]
        if echonet.EPC_瞬時電力計測値 in propdict:
            瞬時電力 = struct.unpack_from("!l", propdict[echonet.EPC_瞬時電力計測値])[0]
        if echonet.EPC_瞬時電流計測値 in propdict:
            瞬時電流_R = struct.unpack_from("!h", propdict[echonet.EPC_瞬時電流計測値])[0]
            瞬時電流_T = struct.unpack_from("!h", propdict[echonet.EPC_瞬時電流計測値], 2)[0]

        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.power_log(係数, 積算電力量, 電力量単位, 瞬時電力, 瞬時電流_R, 瞬時電流_T)
        del store

        return True

    def log_temp(self) -> None:
        """温度を記録する."""
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp: int = int(f.readline())

        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.temp_log(temp)
        del store

    def task(self) -> None:
        """1分間隔で繰り返し実行."""
        interval: int = 60
        while True:
            timestamp: int = int(time.time()) // interval
            if self.connected:
                if not self.get_prop():
                    break
            if self.temp_flag:
                self.log_temp()
            now: float = time.time()
            now_t: int = int(now) // interval
            if timestamp == now_t:
                time.sleep((now_t + 1) * interval - now)


if __name__ == "__main__":
    pc: PowerConsumption = PowerConsumption()
    pc.main()
