"""ECHONET の電文クラス."""

import dataclasses
import struct
import typing as typ

# 定数定義
EHD1: int = 0x10  # プロトコル種別: ECHONET Lite規格
EHD2: int = 0x81  # 形式1
EOJ_CONTROLLER: int = 0x05FF  # 管理・操作関連機器クラスグループ/コントローラ
EOJ_SMARTMETER: int = 0x0288  # 住宅・設備関連機器クラスグループ/低圧スマート電力量メータ
ESV_SetI: int = 0x60  # プロパティ値書き込み要求（応答不要）
ESV_Get: int = 0x62  # プロパティ値読み出し要求
ESV_Get_Res: int = 0x72  # プロパティ値読み出し応答
EPC_瞬時電力計測値: int = 0xE7
EPC_瞬時電流計測値: int = 0xE8


@dataclasses.dataclass
class EProperty:
    """ECHONET プロパティ."""

    epc: int = EPC_瞬時電力計測値
    edt: typ.List[int] = dataclasses.field(default_factory=list)

    def add_data(self, d: int) -> None:
        """データを追加する.

        Args:
            d: データ
        """
        self.edt.append(d)

    def to_bytes(self) -> bytes:
        """byte表記を返す.

        Returns:
            byte表記のEDATA
        """
        return bytes([self.epc, len(self.edt), *self.edt])

    def hex(self) -> str:
        """16進文字列表記を返す.

        Returns:
            16進文字列表記
        """
        return self.to_bytes().hex()

    @classmethod
    def from_bytes(cls, b: bytes, offset: int = 0) -> typ.Tuple["EProperty", int]:
        """byte列からEPropertyインスタンスを生成する.

        Args:
            b: byte列
            offset: byte列の読み込み位置

        Returns:
            EProperty
            次のoffset
        """
        epc: int
        pdc: int
        edt: typ.List[int] = []
        epc, pdc = struct.unpack_from("BB", b, offset)
        if pdc > 0:
            edt = list(struct.unpack_from("B" * pdc, b, offset + 2))
        return EProperty(epc, edt), offset + 2 + pdc


@dataclasses.dataclass
class ECHONETLiteFrame:
    """電文フレーム.

    Attributes:
        ehd: (2B)ECHONETヘッダ
        tid: (2B)トランザクションID
        seoj_c: (2B)送信元オブジェクトクラスグループ/クラスコード
        seoj_i: (1B)送信元オブジェクトインスタンスコード
        deoj_c: (2B)送信先オブジェクトクラスグループ/クラスコード
        deoj_i: (1B)送信先オブジェクトインスタンスコード
        esv: (1B)ECHONET Lite サービス
        edata: EDATAのリスト
    """

    ehd: int = (EHD1 << 8) + EHD2
    tid: int = 1
    seoj_c: int = EOJ_CONTROLLER
    seoj_i: int = 1
    deoj_c: int = EOJ_SMARTMETER
    deoj_i: int = 1
    esv: int = ESV_Get
    properties: typ.List[EProperty] = dataclasses.field(default_factory=list)

    def add_property(self, p: EProperty) -> None:
        """プロパティ追加.

        Args:
            p: EProperty
        """
        self.properties.append(p)

    def to_bytes(self) -> bytes:
        """byte表記を返す.

        Returns:
            byte表記のEDATA
        """
        return (
            struct.pack(
                "!HHHBHBBB",
                self.ehd,
                self.tid,
                self.seoj_c,
                self.seoj_i,
                self.deoj_c,
                self.deoj_i,
                self.esv,
                len(self.properties),
            )
            + b"".join([p.to_bytes() for p in self.properties])
        )

    def hex(self) -> str:
        """16進文字列表記を返す.

        Returns:
            16進文字列表記
        """
        return self.to_bytes().hex()

    @classmethod
    def from_bytes(cls, b: bytes) -> "ECHONETLiteFrame":
        """byte列からECHONETLiteFrameインスタンスを生成する.

        Args:
            b: byte列

        Returns:
            ECHONETLiteFrame
        """
        ehd: int
        tid: int
        seoj_c: int
        seoj_i: int
        deoj_c: int
        deoj_i: int
        esv: int
        opc: int
        properties: typ.List[EProperty] = []

        ehd, tid, seoj_c, seoj_i, deoj_c, deoj_i, esv, opc = struct.unpack_from("!HHHBHBBB", b)
        offset: int = 12
        if opc > 0:
            p: EProperty
            p, offset = EProperty.from_bytes(b, offset)
            properties.append(p)
        return ECHONETLiteFrame(ehd, tid, seoj_c, seoj_i, deoj_c, deoj_i, esv, properties)

    @classmethod
    def from_hex(cls, h: str) -> "ECHONETLiteFrame":
        """hex文字列からECHONETLiteFrameインスタンスを生成する.

        Args:
            h: hex文字列

        Returns:
            ECHONETLiteFrame
        """
        return ECHONETLiteFrame.from_bytes(bytes.fromhex(h))
