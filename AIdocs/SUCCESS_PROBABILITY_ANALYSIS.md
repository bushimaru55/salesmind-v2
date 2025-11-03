# 詳細診断モード - 商談成功率リアルタイム分析 機能仕様

## 1. 機能概要

- **目的**: 詳細診断モードで営業担当者（ユーザー）が送信する各メッセージに対し、会話内容を分析して商談成功率（0〜100%）をリアルタイムに更新する。
- **効果**: 質の高い質問が成功率を引き上げ、浅い質問は成功率を下げることで、ユーザーが会話の質を即座に把握できる。
- **対象モード**: 詳細診断モードのみ（簡易診断モードは対象外）。
- **更新タイミング**: ユーザーがチャットでメッセージを送るたび（= `chat_session` API 呼び出しごと）。
- **初期値**: 詳細診断モードでセッション開始時に 50%（設定可能）。

## 2. 画面/UI 仕様

- チャット画面（`step3`）に「商談成功率」パネルを追加。
    - 表示項目
        - 現在の成功率（例: `商談成功率: 54%`）
        - 前回からの変化量（例: `+4%` / `-3%`）
        - 変動理由（例: 「課題を具体的に掘り下げたため」）
- 成功率はリアルタイムに更新し、変動時は軽いアニメーションで強調。
- ログビューアーにも、成功率変動ログを出力して学習に活用。

## 3. データモデル

### 3.1 `Session` モデル拡張

- フィールド追加例
    ```python
    success_probability = models.IntegerField(default=50, help_text="現在の商談成功率 (0-100%)")
    last_analysis_reason = models.TextField(null=True, blank=True, help_text="直近の変動理由")
    ```
- 初期化: `start_session` 詳細診断モードで 50% にセット。

### 3.2 `ChatMessage` 拡張（オプション）

- 各メッセージに分析結果を紐付ける場合は以下のフィールドを検討。
    ```python
    success_delta = models.IntegerField(null=True, blank=True, help_text="この発言による成功率変動")
    analysis_summary = models.TextField(null=True, blank=True, help_text="分析サマリー")
    ```
- 必須ではないが、チャート表示やレポート機能拡張に備えて持っておくと便利。

## 4. API 仕様

### 4.1 `POST /api/session/chat/`

- **入力**: 既存仕様通り (`session_id`, `message`)。
- **処理フロー追加**:
    1. 既存どおりメッセージを保存。
    2. 詳細診断モードかつ `session.company` が存在する場合のみ分析を実行。
    3. OpenAI による会話分析サービス（`conversation_analysis.analyze_sales_message`）を呼び出し、以下の情報を取得。
        - `current_spin_stage`: 会話全体から見た現在のSPIN段階（S/P/I/N）
        - `message_spin_type`: 今回の営業発言が属するSPIN段階（S/P/I/N）
        - `step_appropriateness`: 段階の適切性（`ideal` / `appropriate` / `jump` / `regression`）
        - `success_delta`: -5〜+5 の成功率変動値
        - `reason`: 変動理由テキスト（SPIN観点を含む）
        - `notes`: 補足情報（任意）
    4. `success_delta` を `Session.success_probability` に適用し、0〜100 でクリップ。
    5. `ChatMessage.analysis_summary` に SPIN評価の要約（変動理由／段階／適切性）を保存。
    6. 応答 JSON に成功率と SPIN 評価情報をセットしフロントへ返却。

### 4.2 OpenAI プロンプト（分析用）

- 軽量かつ応答速度重視のため `gpt-4o-mini` 継続利用予定。
- プロンプト内容（2025-11 現在）
    - 会話履歴・企業情報・現在の成功率を提示。
    - SPIN 各段階の定義、理想的な進行（S→P→I→N）、段階飛び越し／逆戻り時の減点ルールを明示。
    - JSON 出力に SPIN 判定結果（current_spin_stage / message_spin_type / step_appropriateness）と成功率変動を含めるよう指示。
    - 成功率変動の計算ルール（+5〜-5）をプロンプト内に明文化。

---

## 6. 分析ロジック詳細

### 6.1 成功率変動ルール（2025-11 更新）

- `success_delta` の範囲: -5 〜 +5
- 評価観点
    1. SPIN進行段階が適切か（S→P→I→N の順序、逆戻りや飛び越しの有無）
    2. 現在段階に応じた質問の質（Situation/Problem/Implication/Need-Payoff）
    3. 企業情報や価値提案との関連性
    4. 顧客視点・共感の度合い
- OpenAI 応答には SPIN判定3要素（current_spin_stage, message_spin_type, step_appropriateness）と理由が必須。
- Django 側では値域チェック後、`ChatMessage.analysis_summary` に SPIN 情報を追記。

### 6.2 キャッシュ / コスト対策

- すべての発言で OpenAI を呼ぶとトークン消費が増加するため、以下を検討。
    - 1メッセージごとに 1 回（最初の実装）
    - 後続で「一定間隔のみ分析」などのモードを足せるよう、設定化する

## 7. 実装手順（フェーズ分割）

1. **AIdocs 更新（完了）**
2. **モデル・マイグレーション作成** (`success_probability`, `last_analysis_reason` など)
3. **OpenAI サービス実装**（新規: `services/conversation_analysis.py` など）
4. **`chat_session` 更新**
    - 分析呼び出し
    - 成功率更新＆レスポンス拡張
5. **フロントエンド更新**
    - UI 表示
    - 成功率更新ロジック
6. **テスト & チューニング**
    - 初期値・変動幅調整
    - 長時間会話での遷移確認

## 8. 今後の拡張案

- 成功率の推移グラフ（ラインチャート）表示
- 成功率と SPIN スコアの連携
- 会話終了時レポートに推移とハイライトを掲載
- 変動理由をもとに AI コーチから改善アドバイスを提示

## 9. 注意事項

- 詳細診断モードに限定することで、企業情報を活用した評価に集中。
- 成功率はあくまで「AI による推定」であり、誤差がある旨を UI 上で明示する。
- API 応答が遅延した場合のフォールバック（例: `success_delta = 0`）を実装。

