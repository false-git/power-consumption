"""表示と制御."""

import argparse
import configparser
import time
import yaml  # type: ignore
import gpiozero  # type: ignore
from datetime import datetime
from typing import Optional
from threading import Timer
from watchfiles import watch

from oled_ssd1306 import Display
from light import Light

debug_mode: bool = False


def debug(msg: str) -> None:
    """デバッグ表示."""
    if debug_mode:
        print(f"{datetime.now()} {msg}")


class DisplayController:
    """LEDの表示と制御をつかさどるクラス."""

    def __init__(self) -> None:
        """初期化."""
        inifile: configparser.ConfigParser = configparser.ConfigParser()
        inifile.read("power_consumption.ini", "utf-8")
        self.inifile: configparser.ConfigParser = inifile

    def main(self) -> None:
        """メイン処理."""
        global debug_mode
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        parser.add_argument("-d", "--debug", action="store_true", help="enable debug log")
        args: argparse.Namespace = parser.parse_args()
        debug_mode = args.debug

        display_address: int = self.inifile.getint("ssd1306", "address", fallback=0x3C)
        self.data_path: str = self.inifile.get("ssd1306", "data_path", fallback="display.dat")
        button_pin: str = self.inifile.get("ssd1306", "pin", fallback="4")
        button_pull_up: bool = self.inifile.getboolean("ssd1306", "pull_up", fallback=False)
        door_pin: str = self.inifile.get("ssd1306", "door_pin", fallback="21")
        door_pull_up: bool = self.inifile.getboolean("ssd1306", "door_pull_up", fallback=True)
        contrast: int = self.inifile.getint("ssd1306", "contrast", fallback=1)
        token: str = self.inifile.get("switchbot", "token")
        secret: str = self.inifile.get("switchbot", "secret")
        device_id: str = self.inifile.get("switchbot", "device_id")

        self.display: Display = Display(display_address, contrast)
        self.button: gpiozero.Button = gpiozero.Button(button_pin, pull_up=button_pull_up)
        self.door: gpiozero.Button = gpiozero.Button(door_pin, pull_up=door_pull_up)
        self.light_timer: Optional[Timer] = None
        self.light: Light = Light(token, secret, device_id)

        self.is_pressed: bool = self.button.is_pressed
        self.is_opend: bool = not self.door.is_pressed
        if not self.is_pressed:
            self.display.clear()
        self.last_released: float = time.perf_counter()

        if self.is_opend and not self.is_pressed:
            self.light_timer_start()

        self.button.when_pressed = self.pressed
        self.button.when_released = self.released
        self.door.when_pressed = self.closed
        self.door.when_released = self.opend

        self.update()

        for _ in watch(self.data_path):
            self.update()

    def pressed(self) -> None:
        """ボタンが押されたとき."""
        debug("pressed")
        self.is_pressed = True
        if not self.display.is_display:
            self.display.redraw()
        self.light.turn_on()
        self.light_timer_stop()

    def released(self) -> None:
        """ボタンが離されたとき."""
        debug("released")
        self.is_pressed = False
        self.last_released = time.perf_counter()
        if self.is_opend:
            self.light_timer_start()

    def closed(self) -> None:
        """ドアが閉じたとき."""
        debug("door closed")
        self.is_opend = False
        self.light_timer_stop()

    def opend(self) -> None:
        """ドアが開いたとき."""
        debug("door opend")
        self.is_opend = True
        if not self.is_pressed:
            self.light_timer_start()

    def light_timer_start(self) -> None:
        """消灯タイマ開始."""
        if self.light_timer is None:
            debug("start light_timer")
            self.light_timer = Timer(30, self.light_timeout)
            self.light_timer.start()

    def light_timer_stop(self) -> None:
        """消灯タイマ停止."""
        if self.light_timer is not None:
            debug("stop light_timer")
            self.light_timer.cancel()
            self.light_timer = None

    def light_timeout(self) -> None:
        """消灯タイムアウト."""
        debug("light_timeout")
        self.light_timer = None
        if not self.light.turn_off():
            # 失敗したら30秒後にリトライ
            self.light_timer_start()

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
