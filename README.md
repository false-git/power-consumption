# power-consumption

スマートメーターから ECHONET Lite 経由で消費電力を読み出します。

## 参考

* [Skyley Networks　/　Bルートやってみた](http://www.skyley.com/products/b-route.html)
* [スマートメーターの情報を最安ハードウェアで引っこ抜く - Qiita](https://qiita.com/rukihena/items/82266ed3a43e4b652adb)
* [Pythonでスマートメーターの情報を引っこ抜く - Qiita](https://qiita.com/kanon700/items/d4df13d45c2a9d16b8b0)

## ECHONET Lite

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
* OPC(1B): プロパティ数
* EPC(1B): ECHONET プロパティ
  * オブジェクト毎に異なる。スマートメータは、AppendixHのp.312
  * 0xE2: 積算電力量計測値履歴１(正方向計測値)
  * 0xE5: 積算履歴収集日１
  * 0xE7: 瞬時電力計測値
  * 0xE8: 瞬時電流計測値
* PDC(1B): EDTのバイト数
* EDT: プロパティ値データ

