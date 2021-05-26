"""SSD1306 OLED Display."""
import time
import typing as typ
import board
import adafruit_ssd1306
import gpiozero
from PIL import Image, ImageDraw, ImageFont

WIDTH: int = 128
HEIGHT: int = 64


class Display:
    """OLED Display."""

    def __init__(self, address: int, pin: str) -> None:
        """初期化.

        Args:
            address: OLED の I²Cアドレス
            pin: スイッチのpinアドレス
        """
        i2c: board.I2C = board.I2C()
        self.oled: adafruit_ssd1306.SSD1306_I2C = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=address)
        self.image: Image = Image("1", (self.oled.width, self.oled.height))
        self.draw: ImageDraw = ImageDraw(self.image)
        self.font: ImageFont = ImageFont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        self.button: gpiozero.Button = gpiozero.Button(pin)
        self.is_pressed: bool = self.button.is_pressed
        self.is_display: bool = False
        self.clear()
        self.is_display = self.is_pressed
        self.last_released: float = time.perf_counter()
        self.button.when_pressed = self.pressed
        self.button.when_released = self.released

    def clear(self) -> None:
        """画面消去."""
        self.is_display = False
        self.oled.fill(0)
        self.oled.show()

    def redraw(self)->None:
        """画面描画."""
        self.oled.image(self.image)
        self.oled.show()
        self.is_display = True

    def update(self, co2: typ.Optional[int], temp: typ.Optional[float], hum: typ.Optional[float], pres: typ.Optional[float]) -> None:
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
            self.draw.text((0, y), f"気圧 {pres:6.1f} %", font=self.font, fill=255)
            y += 16

        if self.is_display:
            if not self.is_pressed and time.perf_counter() > self.last_released + 30:
                self.clear()
            else:
                self.redraw()

    def pressed(self) -> None:
        self.is_pressed = True
        if not self.is_display:
            self.redraw()

    def released(self) -> None:
        self.is_pressed = False
        self.last_released = time.perf_counter()

if __name__ == "__main__":
    display: Display = Display(0x3c, "4")
    display.update(800, 12.3, 34.5, 1234.5)
    time.sleep(10)
