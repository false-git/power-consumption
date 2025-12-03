"""Light on SwitchBot."""

import time
from typing import Optional
from switchbot import SwitchBot, Device  # type: ignore


class Light:
    """Light."""

    def __init__(self, token: str, secret: str, device_id: str) -> None:
        """初期化.

        Args:
            token: APIアクセストークン
            secret: アクセスシークレット
            device_id: 制御するデバイスID
        """
        self.token: str = token
        self.secret: str = secret
        switchbot: SwitchBot = SwitchBot(token=token, secret=secret)
        self.light: Optional[Device] = None
        self.cache_time: float = 0.0
        self.is_on_cache: bool = False
        if device_id:
            for device in switchbot.devices():
                if device.id == device_id:
                    self.light = device
                    self.is_on_cache = self.is_on()

    def is_on(self) -> bool:
        """ライトがついているか.

        Returns:
            ライトがついていたらTrue

        このメソッドを呼ぶときはself.light.clientが有効であること

        最後に問い合わせてから30分間はAPIに問い合わせしない。
        """
        now: float = time.perf_counter()
        if self.light and now - self.cache_time > 30 * 60:
            try:
                self.is_on_cache = self.light.status()["power"] == "on"
                self.cache_time = now
            except Exception as exc:
                print(exc)
        return self.is_on_cache

    def turn_on(self) -> None:
        """ライトをつける."""
        if self.light:
            switchbot: SwitchBot = SwitchBot(token=self.token, secret=self.secret)
            self.light.client = switchbot.client
            try:
                if not self.is_on():
                    self.light.command("turnOn")
                    self.is_on_cache = True
                    self.cache_time = time.perf_counter()
            except Exception as exc:
                print(exc)

    def turn_off(self) -> bool:
        """ライトを消す.

        Returns:
            成功したらTrue
        """
        result: bool = False
        if self.light:
            switchbot: SwitchBot = SwitchBot(token=self.token, secret=self.secret)
            self.light.client = switchbot.client
            try:
                if self.is_on():
                    self.light.command("turnOff")
                    self.is_on_cache = False
                    self.cache_time = time.perf_counter()
                result = True
            except Exception as exc:
                print(exc)
        return result
