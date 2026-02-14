// src/lib/microcms.ts
import { createClient } from "microcms-js-sdk";

// Cloudflare Pages の Environment variables に設定
const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;

// microCMS側の「コンテンツAPI名」
const ENDPOINT_ARTICLES = "articles";

// category は「文字列 / オブジェクト / 配列」どれでも来うる
export type MicroCMSCategoryItem =
  | string
  | { id?: string; name?: string; slug?: string }
  | null
  | undefined;

export type MicroCMSCategory = MicroCMSCategoryItem | MicroCMSCategoryItem[];

// 記事（body固定）
export type MicroCMSArticle = {
  id: string;
  title?: string;
  description?: string;

  // 本文は body のみを使う
  body?: string;

  category?: MicroCMSCategory;

  date?: string;
  publishedAt?: string;
  revisedAt?: string;
  createdAt?: string;
  updatedAt?: string;
};

// 本文を安全に取り出す（undefined対策）
export function getArticleBody(a: MicroCMSArticle | null | undefined): string {
  return (a?.body ?? "").toString();
}

// ---- カテゴリ正規化 ----
export function normalizeCategoryItem(
  cat: MicroCMSCategoryItem
): { label: string; slug: string } | null {
  if (!cat) return null;

  if (typeof cat === "string") {
    const s = cat.trim();
    if (!s) return null;
    return { label: s, slug: s }; // ★encodeしない
  }

  const label = (cat.name || cat.slug || cat.id || "").trim();
  if (!label) return null;

  const raw = (cat.slug && cat.slug.trim()) || (cat.id && cat.id.trim()) || label;

  return { label, slug: raw }; // ★encodeしない
}

export function normalizeCategories(
  cat: MicroCMSCategory
): { label: string; slug: string }[] {
  if (!cat) return [];

  const items = Array.isArray(cat) ? cat : [cat];

  const normalized = items
    .map((c) => normalizeCategoryItem(c))
    .filter((x): x is { label: string; slug: string } => Boolean(x));

  // slugで重複排除
  const map = new Map<string, { label: string; slug: string }>();
  for (const n of normalized) {
    if (!map.has(n.slug)) map.set(n.slug, n);
  }

  return Array.from(map.values());
}

export function normalizeCategory(
  cat: MicroCMSCategory
): { label: string; slug: string } | null {
  const list = normalizeCategories(cat);
  return list.length ? list[0] : null;
}

// envが未設定のとき、ビルドを落とさず空配列で返す
function canUseMicroCMS() {
  return Boolean(serviceDomain && apiKey);
}

const client = canUseMicroCMS() ? createClient({ serviceDomain, apiKey }) : null;

export async function fetchAllArticles(): Promise<MicroCMSArticle[]> {
  if (!client) return [];

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

export async function fetchArticleById(
  id: string
): Promise<MicroCMSArticle | null> {
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

export const microcms = client;