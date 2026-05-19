# Shiolab Data Story

## URL

- `/sites/shiojiri/`
- `/sites/nagano/`

## Local

```bash
python -m http.server
```

Repository root:

- `http://localhost:8000/public/sites/shiojiri/`

If `public/` is document root:

- `http://localhost:8000/sites/shiojiri/`

## 長野県版の知事・イベント

長野県版では、既存コードの読み込み名を変えないため、`mayors.json` を知事任期帯として使用しています。

追加・更新したファイル:

```text
public/sites/nagano/data/mayors.json
public/sites/nagano/data/timeline_events.json
```
