# power-consumption

スマートメーターから ECHONET Lite 経由で消費電力を読み出します。

## 使い方

* python 3.7.1 以上と、poetry が使える状態にします。
* postgresql に専用のデータベースを作成します。
  * psql で DB に接続し、`\i init.sql` でテーブルを作成します。
* power_consumption.ini-sample を power_consumption.ini にコピーし、必要な項目を設定します。
* スマートメーターから情報を取得する側
  * `poetry install --no-dev -E poller` で実行環境を整えます。
  * `poetry run python power_consumption.py` でデータを収集して DB に格納します。
  * `poetry run python power_consumption.py -t` でCPU温度データも収集するようになります。(Raspberry pi専用)
    * `-c` オプションを付けると、MH-Z19系のCO2センサーの値も収集します。
    * `-b` オプションを付けると、BME280のセンサーの値も収集します。
* 収集したデータからグラフを作る側
  * `poetry install --no-dev -E graph` で実行環境を整えます。
  * `poetry run python power_graph.py` で当日分の電力消費量グラフを生成します。
  * `poetry run python temp_graph.py` で当日分の温度グラフを生成します。
* それぞれ、-h をつけて実行するとヘルプが出ます。

## 参考

* [Skyley Networks　/　Bルートやってみた](http://www.skyley.com/products/b-route.html)
* [スマートメーターの情報を最安ハードウェアで引っこ抜く - Qiita](https://qiita.com/rukihena/items/82266ed3a43e4b652adb)
* [Pythonでスマートメーターの情報を引っこ抜く - Qiita](https://qiita.com/kanon700/items/d4df13d45c2a9d16b8b0)

### ECHONET Lite

* エコーネット規格（一般公開） | ECHONET
  * [ECHONET Lite規格書 Ver.1.12（日本語版）のダウンロード ファイルリスト](https://echonet.jp/spec_v112_lite/)
    * [第2部 ECHONET Lite 通信ミドルウェア仕様](https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/ECHONET_lite_V1_12_jp/ECHONET-Lite_Ver.1.12_02.pdf)
  * [APPENDIX ECHONET機器オブジェクト詳細規定 Release Hのダウンロード ファイルリスト](https://echonet.jp/spec_object_rh/)
    * [APPENDIX ECHONET機器オブジェクト詳細規定 Release H](https://echonet.jp/wp/wp-content/uploads/pdf/General/Standard/Release/Release_H_jp/Appendix_H.pdf)

* 電文 = EHD + TID + EDATA
* EHD(2B): ECHONETヘッダ。ここでは、0x1081 固定だと思って良い。
* TID(2B): トランザクションID。応答のときは要求と同じもの。
* EDATA = SEOJ + DEOJ + ESV + OPC + EPC1 + PDC1 + EDT1 + ・・・ + EPCn + PDCn + EDTn
* SEOJ: 送信元オブジェクト
* DEOJ: 送信先オブジェクト
  * EOJ(3B): ECHONET Lite オブジェクト
    * [X1.X2] [X3] と表現
    * X1: クラスグループコード
    * X2: クラスコード
    * X3: インスタンスコード
    * 05FF01: 管理・操作関連機器クラスグループ/コントローラ/1番
    * 0EF001: プロファイルクラスグループ/ノードプロファイル/1番
    * 028801: 住宅・設備関連機器クラスグループ/低圧スマート電力量メータ/1番
* ESV(1B): ECHONET Liteサービス
  * 0x60: プロパティ値書き込み要求（応答不要）SetI
  * 0x61: プロパティ値書き込み要求（応答要）SetC
  * 0x62: プロパティ値読み出し要求 Get
  * 0x71: プロパティ値書き込み応答 Set_Res
  * 0x72: プロパティ値読み出し応答 Get_Res
  * 0x73: プロパティ値通知 INF (30分に一回勝手に送ってくる)
* OPC(1B): プロパティ数
* EPC(1B): ECHONET プロパティ
  * オブジェクト毎に異なる。スマートメータは、AppendixHのp.312
  * 0xE2: 積算電力量計測値履歴１(正方向計測値)
  * 0xE5: 積算履歴収集日１
  * 0xE7: 瞬時電力計測値
  * 0xE8: 瞬時電流計測値
* PDC(1B): EDTのバイト数
* EDT: プロパティ値データ

### SKコマンド

* コマンドマニュアルは、モジュールのメーカーのサイトからダウンロードする。
  * ROHMも、TESSERAも、マニュアルはパスワードがないとダウンロードできない。(ので、ここにはURLを書かない)
* 応答がないコマンドは、`OK` が返る。(失敗したときは `FAIL ERxx` が返る)
* 応答があるコマンドは、応答の後に `OK`が返る。
  * SKINFO → EINFO
  * SKSREG(読み出し) → ESREG
* FAILのエラーコード
  * ER04: 指定されたコマンドがサポートされていない
  * ER05: 指定されたコマンドの引数の数が正しくない
  * ER06: 指定されたコマンドの引数形式や値域が正しくない
  * ER09: UART 入力エラーが発生した
  * ER10: 指定されたコマンドは受付けたが、実行結果が失敗した
* コマンドの応答以外に、非同期に(?)イベントが発生するらしい
  * ERXUDP
  * ERXTCP
  * EPONG
  * ETCP
  * EADDR
  * ENEIGHBOR
  * EPANDESC
  * EEDSCAN
  * EHANDLE
  * EVENT
    * 0x20: Beaconを受信した
    * 0x21: UDP送信完了
    * 0x24: PANA接続失敗
    * 0x25: PANA接続成功
    * 0x26: 接続相手からセッション終了要求を受信した
    * 0x29: セッションのライフタイムが経過して期限切れになった
      * これを受信したら、再接続のシーケンスが走るので、0x24か0x25が来るまで通信をやめた方が良いらしい。
* SKSCAN: スキャン
  * MODE: 2を指定するとアクティブスキャン(Information Elementあり)
  * CHANNELMASK: FFFFFFFF で全チャンネル
  * DURATION: 各チャンネルのスキャン時間。`0.01 sec * (2^<DURATION> + 1)`
    * 0-14, 6以上推奨
* SKSENDTO: UDP送信
  * HANDLE: ハンドル。良くわからないけど1で良い。
  * IPADDR: 送信先のIPv6アドレス
  * PORT: ポート番号。ECHONET は 3610(0E1A)固定。
  * SEC: セキュリティフラグ。1を指定
  * DATALEN: DATAのバイト数(4桁の16進数)
  * DATA: ここだけバイナリ。ECHONET電文を指定する。
* ERXUDP: UDP受信
  * SENDER: 送信元IPv6アドレス
  * DEST: 送信先IPv6アドレス
  * RPORT: 送信元ポート
  * LPORT: 送信先ポート
  * SENDERLLA: 送信元MACアドレス
  * SECURED: 暗号化されていたら1
  * DATALEN: DATAのバイト数(4桁の16進数)
  * DATA: データ(16進数文字列)

#### 使いそうなシーケンス

* アクティブスキャン
  * →`SKSCAN 2 FFFFFFFF 6`
  * ←`OK`
  * ←`EVENT 20`
  * ←`EPANDESC`
  * ←`  Channel:39`
  * ←`  Pan ID:FFFF`
  * ←`  Addr:FFFFFFFFFFFFFFFF`
  * ←(他にも来るが、使うのは上くらい)
  * ←`EVENT 22 FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX`
  * アクティブスキャンでは、Pairing IDが一致した相手だけが応答してくる。
  * Pairing IDは、SKSETRBIDで設定した Route B ID の末尾8byte
* MACアドレス→IPv6アドレス変換
  * →`SKLL64 XXXXXXXXXXXXXXXX`
  * ←`FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX`
  * これだけ、OKとかExxxとかなしでアドレスが返ってくる。
* PANA接続シーケンス
  * →`SKJOIN FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX`
  * ←`OK`
  * ←`EVENT 25 FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX 00`
  * 接続失敗のときは EVENT 24 が返ってくる。
* 瞬時電力計測値の読み出し
  * →`SKSENDTO 1 FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX 0E1A 1 000E`
  * ←`EVENT 21 FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX 00`
  * ←`OK`
  * ←`ERXUDP FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX FE80:0000:0000:0000:XXXX:XXXX:XXXX:XXXX 0E1A 0E1A XXXXXXXXXXXXXXXX 1 0012 1081000102880105FF017201E704000002AE`