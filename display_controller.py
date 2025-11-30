"""スマートメーターから電力消費量を読むよ."""

import configparser

import time
import yaml  # type: ignore
import gpiozero  # type: ignore
from watchfiles import watch
from oled_ssd1306 import Display


class DisplayController:
    """LEDの表示と制御をつかさどるクラス."""

    def __init__(self) -> None:
        """初期化."""
        inifile: configparser.ConfigParser = configparser.ConfigParser()
        inifile.read("power_consumption.ini", "utf-8")
        self.inifile: configparser.ConfigParser = inifile

    def main(self) -> None:
        """メイン処理."""
        display_address: int = self.inifile.getint("ssd1306", "address", fallback=0x3C)
        self.data_path: str = self.inifile.get("ssd1306", "data_path", fallback="display.dat")
        button_pin: str = self.inifile.get("ssd1306", "pin", fallback="4")
        button_pull_up: bool = self.inifile.getboolean("ssd1306", "pull_up", fallback=False)
        contrast: int = self.inifile.getint("ssd1306", "contrast", fallback=1)
        self.display = Display(display_address, contrast)
        self.button: gpiozero.Button = gpiozero.Button(button_pin, pull_up=button_pull_up)
        self.is_pressed: bool = self.button.is_pressed
        if not self.is_pressed:
            self.display.clear()
        self.last_released: float = time.perf_counter()
        self.button.when_pressed = self.pressed
        self.button.when_released = self.released

        self.update()

        for changes in watch(self.data_path):
            self.update()

    def pressed(self) -> None:
        """ボタンが押されたとき."""
        self.is_pressed = True
        if not self.display.is_display:
            self.display.redraw()

    def released(self) -> None:
        """ボタンが離されたとき."""
        self.is_pressed = False
        self.last_released = time.perf_counter()

    def update(self) -> None:
        """画面を更新する."""
        with open(self.data_path, "r") as f:
            data = yaml.safe_load(f)
        self.display.update(data["co2"], data["temp"], data["hum"], data["pres"])
        if self.display.is_display:
            if not self.is_pressed and time.perf_counter() > self.last_released + 30:
                self.display.clear()
            else:
                self.display.redraw()


if __name__ == "__main__":
    dc: DisplayController = DisplayController()
    dc.main()
