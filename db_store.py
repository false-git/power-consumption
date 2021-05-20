"""DBストア."""

import datetime
import typing as typ
import psycopg2  # type: ignore
import psycopg2.extensions  # type: ignore
import psycopg2.extras  # type: ignore


class DBStore:
    """DBストア."""

    def __init__(self, db_url: str) -> None:
        """初期化.

        Args:
            db_url: DB の接続文字列
        """
        self.db_url: str = db_url
        self.connection: psycopg2.extensions.connection = None
        self.cursor: psycopg2.extensions.cursor = None
        self.open()

    def __del__(self) -> None:
        """デストラクタ."""
        self.close()

    def open(self) -> None:
        """DB接続をopenする."""
        self.close()  # エラーにするのとどっちが親切でしょうね？
        self.connection = psycopg2.connect(self.db_url)
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self) -> None:
        """DB接続をcloseする."""
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def scan_log(self, channel: int, channel_page: int, pan_id: int, addr: str, lqi: int, pair_id: str) -> None:
        """SKSCANの結果を登録する.

        Args:
            channel: チャンネル
            channel_page: チャンネルページ
            pan_id: PAN ID
            addr: 応答元アドレス
            lqi: 受信したビーコンの受信 RSSI (LQI – 107dBm)
            pair_id: Paring ID
        """
        self.cursor.execute(
            "insert into scan_log (channel, channel_page, pan_id, addr, lqi, pair_id) values (%s, %s, %s, %s, %s, %s)",
            (channel, channel_page, pan_id, addr, lqi, pair_id),
        )
        self.connection.commit()

    def power_log(
        self,
        係数: typ.Optional[int],
        積算電力量: typ.Optional[int],
        電力量単位: typ.Optional[int],
        瞬時電力: typ.Optional[int],
        瞬時電流_R: typ.Optional[int],
        瞬時電流_T: typ.Optional[int],
    ) -> None:
        """スマートメータープロパティの値を登録する.

        Args:
            係数: 係数
            積算電力量: 積算電力量計測値
            電力量単位: 積算電力量単位
            瞬時電力: 瞬時電力計測値
            瞬時電流_R: 瞬時電流計測値(R相)
            瞬時電流_T: 瞬時電流計測値(T相)
        """
        self.cursor.execute(
            "insert into power_log (係数, 積算電力量, 電力量単位, 瞬時電力, 瞬時電流_R, 瞬時電流_T) values (%s, %s, %s, %s, %s, %s)",
            (係数, 積算電力量, 電力量単位, 瞬時電力, 瞬時電流_R, 瞬時電流_T),
        )
        self.connection.commit()

    def temp_log(self, temp: int) -> None:
        """温度を登録する.

        Args:
            temp: 温度
        """
        self.cursor.execute("insert into temp_log (temp) values (%s)", (temp,))
        self.connection.commit()

    def co2_log(self, co2: int, temp: int, pressure: int, ss: int) -> None:
        """温度を登録する.

        Args:
            co2: 二酸化炭素濃度[ppm]
            temp: 温度
            pressure: 謎
            ss: status
        """
        self.cursor.execute(
            "insert into co2_log (co2, temp, pressure, ss) values (%s, %s, %s, %s)", (co2, temp, pressure, ss)
        )
        self.connection.commit()

    def bme280_log(self, temp: float, pressure: float, humidity: float) -> None:
        """BM280の計測結果を登録する.

        Args:
            temp: 温度
            pressure: 気圧
            humidity: 湿度
        """
        self.cursor.execute(
            "insert into bme280_log (temp, pressure, humidity) values (%s, %s, %s)", (temp, pressure, humidity)
        )
        self.connection.commit()

    def select_scan_log(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> typ.List[psycopg2.extras.DictRow]:
        """scan_logからデータ取得.

        Args:
            start_time: 取得範囲の最初(start_timeを含む)
            end_time: 取得範囲の最初(end_timeを含まない)

        Returns:
            データ
        """
        self.cursor.execute(
            "select * from scan_log where created_at >= %s and created_at < %s order by created_at",
            (start_time, end_time),
        )
        return self.cursor.fetchall()

    def select_power_log(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> typ.List[psycopg2.extras.DictRow]:
        """power_logからデータ取得.

        Args:
            start_time: 取得範囲の最初(start_timeを含む)
            end_time: 取得範囲の最初(end_timeを含まない)

        Returns:
            データ
        """
        self.cursor.execute(
            "select * from power_log where created_at >= %s and created_at < %s order by created_at",
            (start_time, end_time),
        )
        return self.cursor.fetchall()

    def select_temp_log(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> typ.List[psycopg2.extras.DictRow]:
        """temp_logからデータ取得.

        Args:
            start_time: 取得範囲の最初(start_timeを含む)
            end_time: 取得範囲の最初(end_timeを含まない)

        Returns:
            データ
        """
        self.cursor.execute(
            "select * from temp_log where created_at >= %s and created_at < %s order by created_at",
            (start_time, end_time),
        )
        return self.cursor.fetchall()

    def select_co2_log(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> typ.List[psycopg2.extras.DictRow]:
        """co2_logからデータ取得.

        Args:
            start_time: 取得範囲の最初(start_timeを含む)
            end_time: 取得範囲の最初(end_timeを含まない)

        Returns:
            データ
        """
        self.cursor.execute(
            "select * from co2_log where created_at >= %s and created_at < %s order by created_at",
            (start_time, end_time),
        )
        return self.cursor.fetchall()

    def select_bmw280_log(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> typ.List[psycopg2.extras.DictRow]:
        """bme280_logからデータ取得.

        Args:
            start_time: 取得範囲の最初(start_timeを含む)
            end_time: 取得範囲の最初(end_timeを含まない)

        Returns:
            データ
        """
        self.cursor.execute(
            "select * from bme280_log where created_at >= %s and created_at < %s order by created_at",
            (start_time, end_time),
        )
        return self.cursor.fetchall()
