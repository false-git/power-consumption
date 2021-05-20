"""access BME280 via I2C."""

import struct
import typing as typ
import smbus


class BME280:
    """BME280."""

    def __init__(
        self,
        bus: int = 1,
        address: int = 0x76,
        *,
        osrs_h: int = 1,
        osrs_t: int = 1,
        osrs_p: int = 1,
        mode: int = 3,
        t_sb: int = 0,
        filter: int = 4,
        spi3w_en: int = 0,
    ) -> None:
        """初期化.

        Args:
            bus: i2cのバス
            address: i2cのアドレス
            osrs_h: 湿度のオーバーサンプリング
                0b000: スキップ(出力は0x8000固定)
                0x001: ×1
                0x010: ×2
                0x011: ×4
                0x100: ×8
                その他: ×16
            osrs_t: 温度のオーバーサンプリング
            osrs_p: 気圧のオーバーサンプリング
            mode: センサーモード
                0b00: スリープモード
                0b01: 強制モード
                0b10: 強制モード
                0b11: 通常モード
            t_sb: 通常モードでの休止時間(以下は抜粋)
                0x000: 0.5[ms]
                0x101: 1000[ms]
                0x111: 20[ms]
            filter: IIRフィルタの係数
                0b000: フィルタオフ
                0x001: 2
                0x010: 4
                0x011: 8
                その他: 16
            spi3w_en: SPIインターフェイスの選択
                0: 4線式
                1: 3線式

        天気の監視の推奨設定:
            mode: 1(強制モード)
            osrs_h: 1(×1)
            osrs_t: 1(×1)
            osrs_p: 1(×1)
            filter: 0(オフ)
        屋内のナビゲーションの推奨設定(デフォルト):
            mode: 3(通常モード)
            t_sb: 0(0.5[ms])
            osrs_h: 1(×1)
            osrs_t: 2(×2)
            osrs_p: 5(×16)
            filter: 4(16)
        スイッチサイエンスのサンプル:
            mode: 3(通常モード)
            t_sb: 5(1000[ms])
            osrs_h: 1(×1)
            osrs_t: 1(×1)
            osrs_p: 1(×1)
            filter: 0(オフ)
        """
        assert osrs_h & 0b111 == osrs_h
        assert osrs_t & 0b111 == osrs_t
        assert osrs_p & 0b111 == osrs_p
        assert mode & 0b11 == mode
        assert t_sb & 0b111 == t_sb
        assert filter & 0b111 == filter
        assert spi3w_en & 0b1 == spi3w_en

        self.bus: smbus.SMBus = smbus.SMBus(bus)
        self.i2c_address: int = address

        ctrl_hum: int = osrs_h
        ctrl_meas: int = (osrs_t << 5) + (osrs_p << 2) + mode
        config: int = (t_sb << 5) + (filter << 2) + spi3w_en
        self.write_reg(0xF2, ctrl_hum)
        self.write_reg(0xF4, ctrl_meas)
        self.write_reg(0xF5, config)

        self.init_calibration()

        self.t_fine: int = 0

    def write_reg(self, reg_address: int, data: int) -> None:
        """レジスタの書き込み.

        Args:
            reg_address: レジスタアドレス
            data: データ(1byte)
        """
        self.bus.write_byte_data(self.i2c_address, reg_address, data)

    def init_calibration(self) -> None:
        """calibrationデータの初期化."""
        calib0: bytes = bytes(self.bus.read_i2c_block_data(self.i2c_address, 0x88, 26))
        calib1: bytes = bytes(self.bus.read_i2c_block_data(self.i2c_address, 0xE1, 7))
        self.dig_T: typ.List[int] = list(struct.unpack("<Hhh", calib0[0:6]))
        self.dig_P: typ.List[int] = list(struct.unpack("<Hhhhhhhhh", calib0[6:24]))
        self.dig_H: typ.List[int] = [*struct.unpack("B", calib0[-1:]), *struct.unpack("<hBbHb", calib1)]
        self.dig_H[3] = (self.dig_H[3] << 4) + (self.dig_H[4] & 0xF)
        self.dig_H[4] = self.dig_H[4] >> 4

    def read_raw(self) -> typ.Tuple:
        """センサの生データを読み込む.

        Returns:
            生データのTuple(気圧、気温、湿度)
        """
        rawdata: bytes = bytes(self.bus.read_i2c_block_data(self.i2c_address, 0xF7, 8))
        pres: typ.Tuple = struct.unpack(">HB", rawdata[0:3])
        pres_raw: int = (pres[0] << 4) + (pres[1] >> 4)
        temp: typ.Tuple = struct.unpack(">HB", rawdata[3:6])
        temp_raw: int = (temp[0] << 4) + (temp[1] >> 4)
        hum_raw: int = struct.unpack(">H", rawdata[6:])[0]
        return (pres_raw, temp_raw, hum_raw)

    def compensate_T(self, adc_T: int) -> int:
        """温度を補正する.

        Args:
            adc_T: センサの生データ

        Returns:
            補正後の値
        """
        var1: int = (((adc_T >> 3) - (self.dig_T[0] << 1)) * self.dig_T[1]) >> 11
        var2: int = (((((adc_T >> 4) - self.dig_T[0]) ** 2) >> 12) * self.dig_T[2]) >> 14
        self.t_fine = var1 + var2
        T: int = (self.t_fine * 5 + 128) >> 8
        return T

    def compensate_P(self, adc_P: int) -> int:
        """気圧を補正する.

        Args:
            adc_P: センサの生データ

        Returns:
            補正後の値
        """
        var1: int = self.t_fine - 128000
        var2: int = var1 * var1 * self.dig_P[5]
        var2 += (var1 * self.dig_P[4]) << 17
        var2 += self.dig_P[3] << 35
        var1 = ((var1 * var1 * self.dig_P[2]) >> 8) + ((var1 * self.dig_P[1]) << 12)
        var1 = (((1 << 47) + var1)) * (self.dig_P[0]) >> 33
        if var1 == 0:
            return 0
        p: int = 1048576 - adc_P
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P[8] * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P[7] * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self.dig_P[6] << 4)
        return p

    def compensate_H(self, adc_H: int) -> int:
        """湿度を補正する.

        Args:
            adc_H: センサの生データ

        Returns:
            補正後の値
        """
        v_x1_u32r: int = self.t_fine - 76800
        v_x1_u32r = ((((adc_H << 14) - (self.dig_H[3] << 20) - (self.dig_H[4] * v_x1_u32r)) + 16384) >> 15) * (
            (
                (
                    ((((v_x1_u32r * self.dig_H[5]) >> 10) * (((v_x1_u32r * self.dig_H[2]) >> 11) + 32768)) >> 10)
                    + 2097152
                )
                * self.dig_H[1]
                + 8192
            )
            >> 14
        )
        v_x1_u32r = v_x1_u32r - (((((v_x1_u32r >> 15) ** 2) >> 7) * self.dig_H[0]) >> 4)
        v_x1_u32r = 0 if v_x1_u32r < 0 else v_x1_u32r
        v_x1_u32r = 419430400 if v_x1_u32r > 419430400 else v_x1_u32r
        return v_x1_u32r >> 12

    def read(self) -> typ.Tuple:
        """センサのデータを読み込む.

        Returns:
            データのTuple(気圧、気温、湿度)
        """
        rawdata: typ.Tuple = self.read_raw()
        temp: int = self.compensate_T(rawdata[1])
        pres: int = self.compensate_P(rawdata[0])
        hum: int = self.compensate_H(rawdata[2])
        return (pres / 256 / 100, temp / 100, hum / 1024)


if __name__ == "__main__":
    bme280: BME280 = BME280()
    r: typ.Tuple = bme280.read()
    print(f"気温: {r[1]:.2f}")
    print(f"湿度: {r[2]:.2f}")
    print(f"気圧: {r[0]:.2f}")
