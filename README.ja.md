# YouTube Channel Operator — Lite（無料）

**YouTube の1週間をコマンド1つで：直近7日 vs その前の7日、新しい動画それぞれを「同じ公開日数時点のあなた自身の中央値」と比較し、今週やるべき1つを提示。プロンプトの推測ではなく、あなたのチャンネルのデータから計算します。**

![同梱サンプルチャンネルでの `yto.py demo` 実行（実際の出力）](docs/demo.gif)

<sub>同梱の**サンプル**チャンネル（架空データ）での実際の実行 · [English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Português](README.pt.md) · 日本語</sub>

## Claude Code へのインストール

```
/plugin marketplace add jmshinhwa/youtube-channel-operator
/plugin install yt-operator-lite@readystack-youtube
```

あとは「**YouTube の週次レポートのデモを見せて**」（ログイン不要）、続けて「**YouTube チャンネルを接続して**」と頼むだけ（[設定は約10分](plugins/yt-operator-lite/docs/SETUP.md)）。日本語のレポート：`--lang ja`。

- 5スキル：`weekly` · `profile` · `chapters` · `check` · `connect` — 計算はスクリプト、Claude は指揮だけ。
- **ご自身の** Google OAuth クライアントで読み取り専用ログイン。データはあなたのPC（`~/.youtube-operator`）にだけ保存。
- Python 標準ライブラリのみ。テストでは60本の週次取得で Data API の1日10,000ユニット中5ユニット。
- Pro（12スキル）：視聴維持率、サムネイル CTR、まだ動画のない検索語句、コメント返信リスト、競合の伸びた動画、来週の計画、月次レビュー → https://getreadystack.com/apps/youtube-channel-operator-skill-pack/

MIT · [ReadyStack](https://getreadystack.com) · YouTube および Google とは関係ありません。
