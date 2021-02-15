"""ダミーデータ作成.

実行すると本日分のダミーデータを作成する。確認等はないので注意。
"""

import configparser
import datetime
import random
import psycopg2  # type: ignore
import psycopg2.extensions  # type: ignore
import psycopg2.extras  # type: ignore


def main() -> None:
    """メイン処理."""
    inifile: configparser.ConfigParser = configparser.ConfigParser()
    inifile.read("power_consumption.ini", "utf-8")
    db_url: str = inifile.get("routeB", "db_url")

    connection: psycopg2.extensions.connection = psycopg2.connect(db_url)
    cursor: psycopg2.extensions.cursor = connection.cursor()

    係数: int = 1
    積算電力量: int = 0
    電力量単位: int = 0
    timestamp: datetime.datetime = datetime.datetime.combine(datetime.date.today(), datetime.time())
    timedelta: datetime.timedelta = datetime.timedelta(minutes=1)
    for idx in range(24 * 60):
        積算電力量 += int(random.uniform(0, 10))
        瞬時電力: int = int(random.uniform(0, 100))
        瞬時電流_R: int = int(random.uniform(0, 100))
        瞬時電流_T: int = int(random.uniform(0, 100))
        cursor.execute(
            "insert into power_log (係数, 積算電力量, 電力量単位, 瞬時電力, 瞬時電流_R, 瞬時電流_T, created_at)"
            " values (%s, %s, %s, %s, %s, %s, %s)",
            (係数, 積算電力量, 電力量単位, 瞬時電力, 瞬時電流_R, 瞬時電流_T, timestamp),
        )
        timestamp += timedelta
    connection.commit()


if __name__ == "__main__":
    main()
