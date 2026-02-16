# LOGICLAB hub (Astro + optional microCMS)

目的:
- 記事(=教育コンテンツ)を中心にしたハブ
- 記事から「型の練習クイズ」へ自然に導線
- Cloudflare Pages で静的デプロイ

## ローカル起動
```bash
npm install
npm run dev
```

## Cloudflare Pages 設定
- Build command: `npm run build`
- Build output directory: `dist`

## microCMS を使う場合（任意）
Cloudflare Pages の Environment Variables に以下を設定:
- `MICROCMS_SERVICE_DOMAIN` 例: `your-service`（`your-service.microcms.io` の `your-service` の部分）
- `MICROCMS_API_KEY` microCMS 管理画面の API Key
- `MICROCMS_ENDPOINT` (任意) 既定は `articles`

設定がない場合は `src/content/articles/*.md` のサンプル記事でビルドされます。

> microCMSが 404 を返す（endpoint未作成など）場合は、ローカル記事にフォールバックしてビルドが落ちないようにしてあります。
