"""SKコマンド."""

import serial
import typing as typ


BAUDRATE = 115200


class SKSerial:
    """SKモジュールとやり取りするシリアル."""

    def __init__(self, device: str) -> None:
        """初期化.

        Args:
            device: SKモジュールのデバイスファイル名
        """
        self.device = device
        self.serial = serial.Serial(device, BAUDRATE)

    def readline(self) -> str:
        """テキストを1行読み込む.

        Returns:
            1行分のテキスト
        """
        return self.serial.readline().decode("utf-8")

    def writeline(self, line: str) -> None:
        """テキストを1行書き込む.

        Args:
            line: 1行分のテキスト
        """
        self.serial.write(f"{line}\r\n".encode("utf-8"))

    def skinfo(self) -> typ.Dict[str, str]:
        """SKINFOコマンドを実行する。

        Returns:
            SKINFOの応答をdictで
        """
        self.writeline("SKINFO")
        result: str = self.readline()
        if result.startswith("SK"):
            result = self.readline()
        result1: typ.List[str] = result.split()
        result2: str = self.readline()
        result_names: typ.Tuple = ("RESPONSE", "IPADDR", "ADDR64", "CHANNEL", "PANID", "ADDR16")
        response: typ.Dict[str, str] = {"RESULT": result2.strip()}
        for name, value in zip(result_names, result1):
            response[name] = value
        return response

    def sksreg(self, reg: int, val: typ.Optional[str] = None) -> typ.Dict[str, str]:
        """SKSREGコマンドを実行する.

        Args:
            reg: Sレジスタ番号
            val: 設定する場合は not None

        Returns:
            応答をdictで
        """
        if val is None:
            self.writeline(f"SKSREG S{reg:02x}")
        else:
            self.writeline(f"SKSREG S{reg:02x} {val}")
        result: str = self.readline()
        if result.startswith("SK"):
            result = self.readline()
        result1: typ.List[str] = result.split()
        result2: str = result
        if val is None:
            result2 = self.readline()
            result_names: typ.Tuple = ("RESPONSE", "VALUE")
        response: typ.Dict[str, str] = {"RESULT": result2.strip()}
        if val is None:
            for name, value in zip(result_names, result1):
                response[name] = value
        return response
