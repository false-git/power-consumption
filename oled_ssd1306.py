"""SSD1306 OLED Display."""

import time
import typing as typ
import board  # type: ignore
import adafruit_ssd1306  # type: ignore
from PIL import Image, ImageDraw, ImageFont  # type: ignore

WIDTH: int = 128
HEIGHT: int = 64


class Display:
    """OLED Display."""

    def __init__(self, address: int, contrast: int) -> None:
        """初期化.

        Args:
            address: OLED の I²Cアドレス
            contrast: 輝度(0〜255)、0で消える。
        """
        i2c: board.I2C = board.I2C()
        self.oled: adafruit_ssd1306.SSD1306_I2C = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=address)
        self.oled.contrast(contrast)
        self.image: Image = Image.new("1", (self.oled.width, self.oled.height))
        self.draw: ImageDraw = ImageDraw.Draw(self.image)
        self.font: ImageFont = ImageFont.truetype("/usr/share/fonts/truetype/horai-umefont/ume-tmo3.ttf", 16)
        self.is_display: bool = True

    def clear(self) -> None:
        """画面消去."""
        self.is_display = False
        self.oled.poweroff()

    def redraw(self) -> None:
        """画面描画."""
        if not self.is_display:
            self.oled.poweron()
            self.is_display = True
        self.oled.image(self.image)
        self.oled.show()

    def update(
        self, co2: typ.Optional[int], temp: typ.Optional[float], hum: typ.Optional[float], pres: typ.Optional[float]
    ) -> None:
        """画面を更新する.

        Args:
            co2: CO₂濃度
            temp: 気温
            hum: 湿度
            pres: 気圧
        """
        self.draw.rectangle([0, 0, WIDTH, HEIGHT], fill=0)
        y: int = 0
        if co2 is not None:
            self.draw.text((0, y), f"CO₂  {co2:6.1f} ppm", font=self.font, fill=255)
            y += 16
        if temp is not None:
            self.draw.text((0, y), f"気温 {temp:6.1f} ℃", font=self.font, fill=255)
            y += 16
        if hum is not None:
            self.draw.text((0, y), f"湿度 {hum:6.1f} %", font=self.font, fill=255)
            y += 16
        if pres is not None:
            self.draw.text((0, y), f"気圧 {pres:6.1f} hPa", font=self.font, fill=255)
            y += 16


if __name__ == "__main__":
    display: Display = Display(0x3C, 1)
    display.update(800, 12.3, 34.5, 1234.5)
    time.sleep(10)
