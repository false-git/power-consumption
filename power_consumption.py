"""スマートメーターから電力消費量を読むよ."""

import argparse
import configparser
from oled_ssd1306 import Display
import re
import struct
import subprocess
import sys
import time
import typing as typ
import db_store
import echonet
import skcommand
import mh_z19
import bme280
import tsl2572


class PowerConsumption:
    """スマートメーターから電力消費量を読むクラス."""

    def __init__(self) -> None:
        """初期化."""
        inifile: configparser.ConfigParser = configparser.ConfigParser()
        inifile.read("power_consumption.ini", "utf-8")
        self.inifile: configparser.ConfigParser = inifile
        device: str = inifile.get("routeB", "device")
        timeout: float = inifile.getfloat("routeB", "timeout", fallback=5)
        debug: bool = inifile.getboolean("routeB", "debug", fallback=False)
        self.routeB_id: str = inifile.get("routeB", "id")
        self.routeB_password: str = inifile.get("routeB", "password")
        self.db_url: str = inifile.get("routeB", "db_url")
        self.zabbix_server: typ.Optional[str] = inifile.get("zabbix", "server")
        self.zabbix_port: int = inifile.getint("zabbix", "port", fallback=10051)
        self.zabbix_host: typ.Optional[str] = inifile.get("zabbix", "host")
        self.zabbix_key_prefix: str = inifile.get("zabbix", "key_prefix", fallback="pc")
        self.zabbix_trap: typ.Optional[typ.TextIO] = None
        self.zabbix_command: typ.List[str] = [
            "zabbix_sender",
            "-z",
            self.zabbix_server,
            "-p",
            f"{self.zabbix_port}",
            "-s",
            self.zabbix_host,
            "-i",
            "zabbix.trap",
        ]

        self.sk: skcommand.SKSerial = skcommand.SKSerial(device, timeout, debug)

        self.connected: bool = False
        self.sk_flag: bool = True
        self.temp_flag: bool = False
        self.co2_flag: bool = False
        self.bme280_flag: bool = False
        self.display_flag: bool = False

    def main(self) -> None:
        """メイン処理."""
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        parser.add_argument("-i", "--info", action="store_true", help="send SKINFO command")
        parser.add_argument("-r", "--reg", help="send SKREG command with register S<REG>")
        parser.add_argument("-v", "--value", help="SKREG command with VALUE")
        parser.add_argument("-t", "--temp", action="store_true", help="log Raspberry pi temp")
        parser.add_argument("-c", "--co2", action="store_true", help="log MH-Z19 CO2")
        parser.add_argument("-b", "--bme280", action="store_true", help="log BME280")
        parser.add_argument("-l", "--tsl2572", action="store_true", help="log TSL2572")
        parser.add_argument("-d", "--display", action="store_true", help="enable display")

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
        self.co2_flag = args.co2
        self.bme280_flag = args.bme280
        self.tsl2572_flag = args.tsl2572
        self.display_flag = args.display
        if self.bme280_flag:
            bus: int = self.inifile.getint("bme280", "bus", fallback=1)
            address: int = self.inifile.getint("bme280", "address", fallback=0x76)
            osrs_h: int = self.inifile.getint("bme280", "osrs_h", fallback=1)
            osrs_t: int = self.inifile.getint("bme280", "osrs_t", fallback=2)
            osrs_p: int = self.inifile.getint("bme280", "osrs_p", fallback=5)
            t_sb: int = self.inifile.getint("bme280", "t_sb", fallback=0)
            filter: int = self.inifile.getint("bme280", "filter", fallback=4)
            self.bme280 = bme280.BME280(
                bus,
                address,
                osrs_h=osrs_h,
                osrs_t=osrs_t,
                osrs_p=osrs_p,
                t_sb=t_sb,
                filter=filter,
            )
        if self.tsl2572_flag:
            tsl2572_bus: int = self.inifile.getint("tsl2572", "bus", fallback=1)
            tsl2572_address: int = self.inifile.getint("tsl2572", "address", fallback=0x39)
            atime: int = self.inifile.getint("tsl2572", "atime", fallback=0xC0)
            again: int = self.inifile.getint("tsl2572", "again", fallback=0)
            self.tsl2572 = tsl2572.TSL2572(tsl2572_bus, tsl2572_address, atime=atime, again=again)
        if self.display_flag:
            display_address: int = self.inifile.getint("ssd1306", "address", fallback=0x3C)
            button_pin: str = self.inifile.get("ssd1306", "pin", fallback="4")
            pull_up: bool = self.inifile.getboolean("ssd1306", "pull_up", fallback=False)
            contrast: int = self.inifile.getint("ssd1306", "contrast", fallback=1)
            self.display = Display(display_address, button_pin, pull_up, contrast)

        if not self.sk.routeB_auth(self.routeB_id, self.routeB_password):
            print("ルートBの認証情報の設定に失敗しました。")
            self.sk_flag = False
            self.sk.close()
        else:
            self.connected = self.scan() and self.join()

        if not self.temp_flag and not self.co2_flag and not self.bme280_flag and not self.sk_flag:
            sys.exit(1)

        try:
            self.task()
        except KeyboardInterrupt:
            pass

        if self.connected:
            self.sk.close()

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
        if not re.match(r"([0-9A-F]{4}:){7}[0-9A-F]{4}", ipv6addr):
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

    def add_zabbix(self, key: str, value: typ.Any) -> None:
        """zabbixに送信するデータを追加する.

        Args:
            key: キー
            value: 値
        """
        if self.zabbix_trap:
            print(f"- {self.zabbix_key_prefix}.{key} {value}", file=self.zabbix_trap)

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

        self.add_zabbix("coefficient", 係数)
        self.add_zabbix("energy", 積算電力量)
        self.add_zabbix("energy_unit", 電力量単位)
        self.add_zabbix("power", 瞬時電力)
        self.add_zabbix("current_R", 瞬時電流_R)
        self.add_zabbix("current_T", 瞬時電流_T)

        return True

    def log_temp(self) -> float:
        """温度を記録する.

        Returns:
            CPU温度
        """
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp: int = int(f.readline())

        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.temp_log(temp)
        del store
        self.add_zabbix("cpu_temperature", temp)
        return float(temp)

    def log_co2(self) -> typ.Tuple[int, float]:
        """CO2を記録する.

        Returns:
            CO2濃度, 気温
        """
        d: typ.Dict = mh_z19.read_all(serial_console_untouched=True)
        self.sk.debug_print(f"MH_Z19: {d}")
        if "co2" in d:
            store: db_store.DBStore = db_store.DBStore(self.db_url)
            store.co2_log(d["co2"], d["temperature"], d["UhUl"], d["SS"])
            del store
            self.add_zabbix("co2", d["co2"])
            return (d["co2"], d["temperature"])
        return (0, 0)

    def log_bme280(self) -> typ.Tuple:
        """BME280の情報を記録する.

        Returns:
            気圧, 気温, 湿度
        """
        d: typ.Tuple = self.bme280.read()
        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.bme280_log(d[1], d[0], d[2])
        del store
        self.add_zabbix("temperature", d[1])
        self.add_zabbix("pressure", d[0])
        self.add_zabbix("humidity", d[2])
        return d

    def log_tsl2572(self) -> typ.Tuple[float, float, float, int, int]:
        """TSL2572の情報を記録する.

        Returns:
            (照度, lux1, lux2, ch0, ch1)
        """
        values: typ.Tuple[float, float, float, int, int] = self.tsl2572.read()
        store: db_store.DBStore = db_store.DBStore(self.db_url)
        store.tsl2572_log(values[0], values[1], values[2], values[3], values[4])
        del store
        self.add_zabbix("illuminance", values[0])
        return values

    def task(self) -> None:
        """1分間隔で繰り返し実行."""
        interval: int = 60
        wait_counter: int = 10
        while True:
            if self.zabbix_server:
                self.zabbix_trap = open("zabbix.trap", "wt")
            next_time: int = (int(time.time()) // interval + 1) * interval
            temp: typ.Optional[float] = None
            hum: typ.Optional[float] = None
            pres: typ.Optional[float] = None
            co2: typ.Optional[int] = None
            if self.temp_flag:
                temp = self.log_temp()
            if self.co2_flag:
                (co2, temp) = self.log_co2()
            if self.bme280_flag:
                (pres, temp, hum) = self.log_bme280()
            if self.tsl2572_flag and self.tsl2572.initialized:
                self.log_tsl2572()
            if self.sk_flag:
                if self.connected:
                    if not self.get_prop():
                        self.sk.debug_print("RETRY OUT")
                        self.connected = False
                        wait_counter = 10
                elif wait_counter > 0:
                    wait_counter -= 1
                else:
                    if self.scan() and self.join() and self.get_prop():
                        self.sk.debug_print("RECOVERY")
                        self.connected = True
                    else:
                        wait_counter = 10
            if self.display_flag:
                self.display.update(co2, temp, hum, pres)
            if self.zabbix_trap:
                self.zabbix_trap.close()
                with open("zabbix.log", "wt") as zabbix_log:
                    subprocess.run(self.zabbix_command, stdout=zabbix_log, stderr=subprocess.STDOUT)
                self.zabbix_trap = None
            now: float = time.time()
            if self.connected:
                while now < next_time:
                    line: str = self.sk.readline(next_time - now)
                    if len(line) == 0 or not line.endswith("\n"):
                        break
                    line = line.replace("\r\n", "")
                    self.sk.debug_print(f"DROP [{line}]")
                    now = time.time()
            elif now < next_time:
                time.sleep(next_time - now)


if __name__ == "__main__":
    pc: PowerConsumption = PowerConsumption()
    pc.main()
