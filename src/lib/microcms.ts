// src/lib/microcms.ts
import { createClient } from "microcms-js-sdk";

// microCMSの環境変数（Cloudflare Pages の Environment variables に設定）
const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;

// microCMS側の「コンテンツAPI名」
// もしあなたのmicroCMSで違う名前なら、ここだけ合わせればOK
const ENDPOINT_ARTICLES = "articles";

// 型（必要最低限）
export type MicroCMSCategory =
  | string
  | { id?: string; name?: string; slug?: string }
  | null
  | undefined;

export type MicroCMSArticle = {
  id: string;
  title?: string;
  description?: string;
  content?: string;
  category?: MicroCMSCategory;
  date?: string;
  publishedAt?: string;
  revisedAt?: string;
  createdAt?: string;
  updatedAt?: string;
};

// categoryを「表示名」と「URL用slug」に正規化（[object Object] 対策）
export function normalizeCategory(cat: MicroCMSCategory): {
  label: string;
  slug: string;
} | null {
  if (!cat) return null;

  if (typeof cat === "string") {
    const s = cat.trim();
    if (!s) return null;
    return { label: s, slug: encodeURIComponent(s) };
  }

  // objectの場合
  const label = (cat.name || cat.slug || cat.id || "").trim();
  if (!label) return null;

  // URLはslug優先、なければid、最後にlabel
  const raw =
    (cat.slug && cat.slug.trim()) ||
    (cat.id && cat.id.trim()) ||
    label;

  return { label, slug: encodeURIComponent(raw) };
}

// envが未設定のとき、ビルドを落とさず空配列で返す（審査・開発時に便利）
function canUseMicroCMS() {
  return Boolean(serviceDomain && apiKey);
}

// clientは「使えるときだけ」作る
const client = canUseMicroCMS()
  ? createClient({ serviceDomain, apiKey })
  : null;

// 全記事（一覧用）
export async function fetchAllArticles(): Promise<MicroCMSArticle[]> {
  if (!client) return [];

  // microCMSは 1回で全件取れないのでループ
  const limit = 100;
  let offset = 0;
  let all: MicroCMSArticle[] = [];

  while (true) {
    const res = await client.getList<MicroCMSArticle>({
      endpoint: ENDPOINT_ARTICLES,
      queries: { limit, offset, orders: "-publishedAt" },
    });

    all = all.concat(res.contents || []);
    offset += limit;

    if (all.length >= (res.totalCount || 0)) break;
    if (!res.contents || res.contents.length === 0) break;
  }

  return all;
}

// 単記事（詳細ページ用）
export async function fetchArticleById(id: string): Promise<MicroCMSArticle | null> {
  if (!client) return null;
  try {
    const res = await client.getListDetail<MicroCMSArticle>({
      endpoint: ENDPOINT_ARTICLES,
      contentId: id,
    });
    return res ?? null;
  } catch {
    return null;
  }
}

export const microcms = client ?? {
  getList: async () => ({ contents: [], totalCount: 0, offset: 0, limit: 0 }),
  getListDetail: async () => null,
};