"""SKコマンド."""

import datetime
import serial  # type: ignore
import typing as typ
import re
import echonet

BAUDRATE = 115200
re_OK: str = r"\s*OK\s*"

PORT_ECHONETLite: str = "0E1A"  # ECHONETLite UDP Port
PORT_PANA: str = "02CC"  # PANA UDP Port
IPv6_ALL: str = "FF02:0000:0000:0000:0000:0000:0000:0001"  # All nodes in the リンクローカル
TIMEOUT_MARK: str = "--TIMEOUT--"  # readlineのTIMEOUTマーク


class SKSerial:
    """SKモジュールとやり取りするシリアル."""

    def __init__(self, device: str, timeout: float, debug: bool) -> None:
        """初期化.

        Args:
            device: SKモジュールのデバイスファイル名
            timeout: UDP受信タイムアウト
            debug: デバッグフラグ
        """
        self.device: str = device
        self.serial: typ.Optional[serial.Serial] = None
        self.timeout: float = timeout
        self.debug: bool = debug
        self.ip: str = ""
        self.tid: int = 0
        self.open()

    def __del__(self) -> None:
        """デストラクタ."""
        self.close()

    def open(self) -> None:
        """シリアル接続をopenする."""
        self.close()
        self.serial = serial.Serial(self.device, BAUDRATE)

    def close(self) -> None:
        """シリアル接続をcloseする."""
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def debug_print(self, text: str) -> None:
        """デバッグプリント.

        Args:
            text: ログ出力する文字列
        """
        if self.debug:
            now: datetime.datetime = datetime.datetime.now()
            print(f"{now} {text}", flush=True)

    def readline(self, timeout: typ.Optional[float]) -> str:
        """テキストを1行読み込む.

        Returns:
            1行分のテキスト
            timeout: timeout
        """
        assert self.serial is not None
        self.serial.timeout = timeout
        return self.serial.readline().decode("utf-8")

    def readresponse(self, cond: str = re_OK, timeout: typ.Optional[float] = None) -> typ.Tuple[bool, typ.List[str]]:
        """応答を読み込む.

        Returns:
            success: 終了条件を満たしたらTrue
            response: 読み込んだ行のリスト
            timeout: timeout
        """
        success: bool = False
        response: typ.List[str] = []
        while True:
            line: str = self.readline(timeout)
            if len(line) == 0 or not line.endswith("\n"):
                self.debug_print(f"RECEIVE [{line}] TIMEOUT")
                response.append(TIMEOUT_MARK)
                break
            line = line.replace("\r\n", "")
            self.debug_print(f"RECEIVE [{line}]")
            if line.startswith("SK"):
                # エコーバックと判断して無視
                continue
            response.append(line)
            if line.startswith("FAIL"):
                # FAILが来たら無条件に終了
                break
            if re.match(cond, line):
                success = True
                break
        return success, response

    def writeline(self, line: str, bin: typ.Optional[bytes] = None) -> None:
        """テキストを1行書き込む.

        Args:
            line: 1行分のテキスト
            bin: バイナリデータ
        """
        assert self.serial is not None
        if self.debug:
            if bin is None:
                self.debug_print(f"SEND [{line}]")
            else:
                self.debug_print(f"SEND [{line}{bin.hex()}]")
        if bin is None:
            self.serial.write(f"{line}\r\n".encode("utf-8"))
        else:
            self.serial.write(line.encode("utf-8") + bin)

    def skinfo(self) -> typ.Dict[str, str]:
        """SKINFOコマンドを実行する.

        Returns:
            SKINFOの応答をdictで
        """
        self.writeline("SKINFO")
        success, response = self.readresponse()
        result: typ.Dict[str, str] = {}
        if success:
            result1: typ.List[str] = response[0].split()
            result_names: typ.Tuple = ("RESPONSE", "IPADDR", "ADDR64", "CHANNEL", "PANID", "ADDR16")
            for name, value in zip(result_names, result1):
                result[name] = value
        else:
            result["RESPONSE"] = response[0]
        return result

    def sksreg(self, reg: int, val: typ.Optional[str] = None) -> typ.Optional[str]:
        """SKSREGコマンドを実行する.

        Args:
            reg: Sレジスタ番号
            val: 設定する場合は not None

        Returns:
            失敗の時はNone、成功のときは読み出した値またはOK
        """
        if val is None:
            self.writeline(f"SKSREG S{reg:02X}")
        else:
            self.writeline(f"SKSREG S{reg:02X} {val}")
        success, response = self.readresponse()

        result: typ.Optional[str] = None
        if success:
            if val is None:
                result1: typ.List[str] = response[0].split(maxsplit=1)
                # 存在しないレジスタを読み出そうとしたときは、空文字列が返る
                if len(result1) > 1:
                    result = result1[1]
            else:
                result = response[0]
        return result

    def routeB_auth(self, id: str, password: str) -> bool:
        """Bルートの認証情報を設定する.

        Args:
            id: 認証ID
            password: パスワード

        Returns:
            成功したらTrue
        """
        plen: int = len(password)
        assert plen > 0 and plen <= 32
        self.writeline(f"SKSETPWD {plen:X} {password}")
        success1, _ = self.readresponse()
        self.writeline(f"SKSETRBID {id}")
        success2, _ = self.readresponse()
        return success1 and success2

    def scan_pan(self) -> typ.Dict[str, str]:
        """PAN の SCANを行う.

        durationの閾値は0〜14
        0.01 sec * (2 ** duration + 1)
        マニュアルでは6以上を推奨。ネットでは、4で十分と言う話や、7で駄目だったら駄目と言う話も。

        マスクの指定はFFFFFFFFだが、マニュアルに載っているのは全部で28チャンネル。
        duration = 4 → 0.17s * 28 = 4.76s (実測で5.47秒)
        duration = 6 → 0.65s * 28 = 18.2s (実測で17.62秒)
        duration = 7 → 1.29s * 28 = 36.12s (実測で34.72秒)

        Returns:
            SCAN結果
        """
        result: typ.Dict[str, str] = {}
        duration: int
        for duration in range(4, 8):
            self.writeline(f"SKSCAN 2 FFFFFFFF {duration:X}")
            success, response = self.readresponse(r"EVENT 22.*")
            if success:
                for line in response:
                    if line.startswith("  "):
                        parts: typ.List[str] = line.strip().split(":")
                        result[parts[0]] = parts[1]
                    elif line.startswith("EVENT 22"):
                        parts = line.strip().split()
                        if len(parts) == 3:
                            self.ip = parts[-1]
                if "Channel" in result and "Pan ID" in result and "Addr" in result:
                    break
                result = {}
        return result

    def skll64(self, addr: str) -> str:
        """MACアドレスをIPv6アドレスに変換.

        Args:
            addr: MACアドレス

        Returns:
            IPv6アドレス。失敗した場合はエラーコード
        """
        self.writeline(f"SKLL64 {addr}")
        success, response = self.readresponse(r"([0-9A-F]{4}:){7}[0-9A-F]{4}")
        return response[0]

    def skjoin(self, ipv6addr: str) -> bool:
        """PAA接続シーケンス.

        Args:
            ipv6addr: 接続先のIPv6アドレス

        Returns:
            成功したらTrue
        """
        self.writeline(f"SKJOIN {ipv6addr}")
        success, response = self.readresponse(r"EVENT 2[45].*")
        for line in response:
            if line.startswith("EVENT 25"):
                return True
        return False

    def get_prop(self, ipv6addr: str, epc_list: typ.List[int]) -> typ.Optional[typ.List[echonet.EProperty]]:
        """プロパティ取得.

        Args:
            ipv6addr: UDP送信先IPv6アドレス
            epc_list: 読み出すプロパティのEPCのリスト

        Returns:
            読み出したプロパティ値。失敗したらNone
        """
        self.tid = (self.tid + 1) & 0xFFFF
        frame: echonet.ECHONETLiteFrame = echonet.ECHONETLiteFrame(tid=self.tid)
        for epc in epc_list:
            frame.add_property(echonet.EProperty(epc))
        bin: bytes = frame.to_bytes()
        success: bool = False
        response: typ.List[str] = [TIMEOUT_MARK]
        timeout_count: int = -1
        while timeout_count < 5:
            if len(response) > 0 and response[-1] == TIMEOUT_MARK:
                self.writeline(f"SKSENDTO 1 {ipv6addr} {PORT_ECHONETLite} 1 {len(bin):04X} ", bin)
                timeout_count += 1
            else:
                timeout_count = 0
            # 細かいことを言えばUDP送信の後、EVENT 21が来て、その後ERXUDPを待つことになるが、送信が失敗たらFAILが来ると想定。
            # FAILの場合にリトライするかは悩みどころ。
            success, response = self.readresponse(r"ERXUDP.*", self.timeout)
            if success:
                for line in response:
                    if line.startswith("ERXUDP"):
                        token: typ.List[str] = line.split()
                        if len(token) == 9:
                            if (
                                token[2] == self.ip
                                and token[4] == f"{PORT_ECHONETLite}"
                                and echonet.check_get_res(token[-1], self.tid)
                            ):
                                frame = echonet.ECHONETLiteFrame.from_hex(token[-1])
                                return frame.properties
                        self.debug_print("telegram not for me.")
        return None
