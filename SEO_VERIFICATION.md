# SEO対策 確認URL・ツール一覧

## 本番環境のページURL

### メインページ
- **アプリ本体**: https://salesmind.mind-bridge.tech/
- **ランディングページ**: https://salesmind.mind-bridge.tech/landing.html

### SEO関連ファイル
- **robots.txt**: https://salesmind.mind-bridge.tech/robots.txt

---

## SEO検証ツール

### 1. Google Search Console
- **URL**: https://search.google.com/search-console
- **確認内容**: 
  - ページのインデックス状況
  - 検索パフォーマンス
  - モバイルユーザビリティ
  - 構造化データのエラー

### 2. Google リッチリザルトテスト
- **URL**: https://search.google.com/test/rich-results
- **確認内容**:
  - JSON-LD構造化データの検証
  - リッチスニペットの表示確認

### 3. Google モバイルフレンドリーテスト
- **URL**: https://search.google.com/test/mobile-friendly
- **確認内容**:
  - モバイル表示の最適化状況

### 4. PageSpeed Insights
- **URL**: https://pagespeed.web.dev/
- **確認内容**:
  - ページの読み込み速度
  - Core Web Vitals
  - パフォーマンススコア

---

## ソーシャルメディア プレビューツール

### 1. Facebook シェアデバッガー
- **URL**: https://developers.facebook.com/tools/debug/
- **確認内容**:
  - Open Graphタグの表示確認
  - シェア時のプレビュー画像・タイトル・説明文

### 2. Twitter Card Validator
- **URL**: https://cards-dev.twitter.com/validator
- **確認内容**:
  - Twitter Cardタグの表示確認
  - ツイート時のプレビュー

### 3. LinkedIn Post Inspector
- **URL**: https://www.linkedin.com/post-inspector/
- **確認内容**:
  - LinkedInシェア時のプレビュー

---

## 構造化データ検証

### Schema.org Markup Validator
- **URL**: https://validator.schema.org/
- **確認内容**:
  - JSON-LD構造化データの構文チェック
  - Schema.org準拠性

---

## その他の確認ツール

### W3C Markup Validator
- **URL**: https://validator.w3.org/
- **確認内容**:
  - HTMLの構文エラー
  - HTML5準拠性

### Lighthouse (Chrome DevTools)
- **使用方法**: Chrome DevTools > Lighthouseタブ
- **確認内容**:
  - SEOスコア
  - パフォーマンススコア
  - アクセシビリティスコア
  - ベストプラクティス

---

## 確認手順（推奨順）

1. **本番環境での表示確認**
   - https://salesmind.mind-bridge.tech/
   - https://salesmind.mind-bridge.tech/landing.html
   - ブラウザの開発者ツールでメタタグを確認

2. **構造化データの検証**
   - https://search.google.com/test/rich-results でJSON-LDを検証

3. **ソーシャルメディアプレビュー**
   - Facebook シェアデバッガーでOGPタグを確認
   - Twitter Card ValidatorでTwitter Cardを確認

4. **SEOスコアの確認**
   - LighthouseでSEOスコアを確認
   - PageSpeed Insightsでパフォーマンスを確認

5. **Google Search Consoleへの登録**（未登録の場合）
   - サイトマップの送信
   - インデックス登録のリクエスト

---

## 確認ポイントチェックリスト

- [ ] ページタイトルが適切に表示されているか
- [ ] メタディスクリプションが検索結果に表示されるか
- [ ] Open Graph画像が正しく表示されるか
- [ ] Twitter Cardが正しく表示されるか
- [ ] JSON-LD構造化データにエラーがないか
- [ ] robots.txtが正しく配信されているか
- [ ] カノニカルURLが設定されているか
- [ ] 画像のalt属性が適切に設定されているか
- [ ] モバイル表示が最適化されているか
- [ ] ページ読み込み速度が適切か



