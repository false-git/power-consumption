"""access TSL2572 via I2C."""
import time
import typing as typ
import smbus

# TSL2572 Register Set

# Command Register
TSL2572_COMMAND = 0x80
TSL2572_TYPE_REP = 0x00  # Repeated byte protocol transaction
TSL2572_TYPE_INC = 0x20  # Auto-increment protocol transaction
TSL2572_TYPE_SFC = 0x60  # Special function
TSL2572_ALSIFC = 0x6  # ALS interrupt clear(TYPE_SFC)

# Enable Register
TSL2572_SAI = 0x40  # Sleep after interrupt
TSL2572_AIEN = 0x10  # ALS interrupt mask
TSL2572_WEN = 0x08  # Wait enable
TSL2572_AEN = 0x02  # ALS Enable
TSL2572_PON = 0x01  # Power ON

# Status Register
TSL2572_AINT = 0x10  # ALS Interrupt.
TSL2572_AVALID = 0x01  # ALS Valid.

# Register ID
TSL2572_ENABLE = 0x00
TSL2572_ATIME = 0x01
TSL2572_WTIME = 0x03
TSL2572_AILTL = 0x04
TSL2572_AILTH = 0x05
TSL2572_AIHTL = 0x06
TSL2572_AIHTH = 0x07
TSL2572_PRES = 0x0C
TSL2572_CONFIG = 0x0D
TSL2572_CONTROL = 0x0F
TSL2572_ID = 0x12
TSL2572_STATUS = 0x13
TSL2572_C0DATA = 0x14
TSL2572_C0DATAH = 0x15
TSL2572_C1DATA = 0x16
TSL2572_C1DATAH = 0x17

AGAIN: typ.List[int] = [1, 8, 16, 120]


class TSL2572:
    """TSL2572."""

    def __init__(
        self,
        bus: int = 1,
        address: int = 0x39,
        *,
        atime: int = 0xC0,
        again: int = 0x0,
    ) -> None:
        """初期化.

        Args:
            bus: i2cのバス
            address: i2cのアドレス
            atime: ALS timing register
                0xff: 2.73ms
                0xf6: 27.3ms
                0xdb: 101ms
                0xc0: 175ms(default)
                0x00: 699ms
            again: ALS Gain
                0x00: 1x gain
                0x01: 8x gain
                0x02: 16x gain
                0x03: 120x gain
        """
        assert atime & 0xFF == atime
        assert again & 0b11 == again

        self.bus: smbus.SMBus = smbus.SMBus(bus)
        self.i2c_address: int = address
        self.atime: int = atime
        self.initialized: bool = False
        self.retryout: bool = False
        GA: int = 1  # glass attenuation
        self.CPL: float = (2.73 * (256 - self.atime) * AGAIN[again]) / (GA * 60.0)

        if self.read_reg(TSL2572_ID) != 0x34:
            # check TSL25721 ID
            return

        # gain(0x00 = 1x)
        self.write_reg(TSL2572_CONTROL, 0x00)
        # AGL(0 = AGAIN scaled by 1), WLONG(WTIME scaled by 1)
        self.write_reg(TSL2572_CONFIG, 0x00)
        # ATIME
        self.write_reg(TSL2572_ATIME, atime)
        # Enable register(Power OFF)
        self.write_reg(TSL2572_ENABLE, 0)

        self.initialized = True

        self.t_fine: int = 0

    def write_reg(self, reg_address: int, data: int) -> None:
        """レジスタの書き込み.

        Args:
            reg_address: レジスタアドレス
            data: データ(1byte)
        """
        self.bus.write_byte_data(self.i2c_address, TSL2572_COMMAND | TSL2572_TYPE_INC | reg_address, data)

    def read_reg(self, reg_address: int) -> int:
        """レジスタの読み込み.

        Args:
            reg_address: レジスタアドレス

        Returns:
            読み出したデータ
        """
        return self.bus.read_byte_data(self.i2c_address, TSL2572_COMMAND | TSL2572_TYPE_INC | reg_address)

    def read_raw(self) -> typ.Tuple[int, int]:
        """センサの生データを読み込む.

        Returns:
            生データのTuple(CH0、CH1)
        """
        # Enable register(Sleep after interrupt, ALS Enable, Power ON)
        self.write_reg(TSL2572_ENABLE, TSL2572_SAI | TSL2572_AEN | TSL2572_PON)
        mask: int = TSL2572_AINT | TSL2572_AVALID
        retryout: bool = True
        for i in range(100):  # 100回までリトライ。0.01秒sleepなので1秒まで
            status: int = self.read_reg(TSL2572_STATUS)
            if status & mask == mask:
                retryout = False
                break
            time.sleep(0.01)
        self.retryout = retryout

        dat: typ.List[int] = self.bus.read_i2c_block_data(
            self.i2c_address, TSL2572_COMMAND | TSL2572_TYPE_INC | TSL2572_C0DATA, 4
        )
        adc0: int = (dat[1] << 8) | dat[0]
        adc1: int = (dat[3] << 8) | dat[2]
        return (adc0, adc1)

    def read(self) -> typ.Tuple[float, float, float, int, int]:
        """センサのデータを読み込む.

        Returns:
            (照度, lux1, lux2, ch0, ch1)
        """
        if not self.initialized:
            return (-1, -1, -1, -1, -1)
        adc: typ.Tuple[int, int] = self.read_raw()
        lux1: float = ((adc[0] * 1.00) - (adc[1] * 1.87)) / self.CPL
        lux2: float = ((adc[0] * 0.63) - (adc[1] * 1.00)) / self.CPL
        return (max(lux1, lux2, 0), lux1, lux2, adc[0], adc[1])


if __name__ == "__main__":
    tsl2572: TSL2572 = TSL2572()
    values: typ.Tuple[float, float, float, int, int] = tsl2572.read()
    print(f"照度: {values[0]:.2f}")
    print(f"LUX1: {values[1]:.2f}")
    print(f"LUX2: {values[2]:.2f}")
    print(f"CH0: {values[3]}")
    print(f"CH1: {values[4]}")
