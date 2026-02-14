// src/lib/microcms.ts
import { createClient } from "microcms-js-sdk";

// microCMSの環境変数（Cloudflare Pages の Environment variables に設定）
const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;

// microCMS側の「コンテンツAPI名」
const ENDPOINT_ARTICLES = "articles";

// category は「文字列」「オブジェクト」「配列」など混ざり得る前提で扱う
export type MicroCMSCategoryItem =
  | string
  | { id?: string; name?: string; slug?: string }
  | null
  | undefined;

export type MicroCMSCategory = MicroCMSCategoryItem | MicroCMSCategoryItem[];

// 本文は content を使わず body を使う前提
export type MicroCMSArticle = {
  id: string;
  title?: string | null;
  description?: string | null;

  // microCMS のリッチテキストが body に入る想定（HTML文字列）
  body?: string | null;

  // 互換用（使わない方針でも残してOK）
  content?: string | null;

  category?: MicroCMSCategory;
  date?: string | null;
  publishedAt?: string | null;
  revisedAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

function canUseMicroCMS() {
  return Boolean(serviceDomain && apiKey);
}

const client = canUseMicroCMS()
  ? createClient({ serviceDomain, apiKey })
  : null;

/**
 * category を「表示名(label)」「URL用slug」に正規化（単体用）
 */
export function normalizeCategory(
  cat: MicroCMSCategory
): { label: string; slug: string } | null {
  if (!cat) return null;

  // 配列なら先頭を採用（単一表示用）
  if (Array.isArray(cat)) {
    for (const item of cat) {
      const normalized = normalizeCategoryItem(item);
      if (normalized) return normalized;
    }
    return null;
  }

  return normalizeCategoryItem(cat);
}

/**
 * category を配列で返す（一覧表示用：複数カテゴリに対応）
 */
export function normalizeCategories(
  cat: MicroCMSCategory
): { label: string; slug: string }[] {
  if (!cat) return [];
  if (!Array.isArray(cat)) {
    const one = normalizeCategoryItem(cat);
    return one ? [one] : [];
  }

  const out: { label: string; slug: string }[] = [];
  const seen = new Set<string>();
  for (const item of cat) {
    const n = normalizeCategoryItem(item);
    if (!n) continue;
    if (seen.has(n.slug)) continue;
    seen.add(n.slug);
    out.push(n);
  }
  return out;
}

function normalizeCategoryItem(
  cat: MicroCMSCategoryItem
): { label: string; slug: string } | null {
  if (!cat) return null;

  if (typeof cat === "string") {
    const s = cat.trim();
    if (!s) return null;
    return { label: s, slug: encodeURIComponent(s) };
  }

  const label = (cat.name || cat.slug || cat.id || "").trim();
  if (!label) return null;

  const raw =
    (cat.slug && cat.slug.trim()) || (cat.id && cat.id.trim()) || label;

  return { label, slug: encodeURIComponent(raw) };
}

// 全記事（一覧用）
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

// 単記事（詳細ページ用）
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