// src/lib/microcms.ts
import { createClient } from "microcms-js-sdk";

// microCMS environment variables
const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;
const endpointArticles = import.meta.env.MICROCMS_ENDPOINT || "articles";

// ---------- Types ----------

export type MicroCMSCategoryItem = {
  id?: string;
  name?: string;
  slug?: string;
};

export type MicroCMSCategory =
  | string
  | MicroCMSCategoryItem
  | MicroCMSCategoryItem[]
  | string[]
  | null
  | undefined;

export type MicroCMSArticle = {
  id: string;
  title?: string;
  description?: string;
  body?: string;
  content?: string;
  category?: MicroCMSCategory;
  date?: string;
  publishedAt?: string;
  revisedAt?: string;
  createdAt?: string;
  updatedAt?: string;
};

// ---------- Helpers ----------

function canUseMicroCMS(): boolean {
  return Boolean(serviceDomain && apiKey);
}

const client = canUseMicroCMS()
  ? createClient({
      serviceDomain,
      apiKey,
    })
  : null;

export const microcms = client;

function normalizeCategoryItem(
  cat: MicroCMSCategoryItem
): { label: string; slug: string } | null {
  if (!cat) return null;

  const label = (cat.name || cat.slug || cat.id || "").trim();
  if (!label) return null;

  const raw =
    (cat.slug && cat.slug.trim()) || (cat.id && cat.id.trim()) || label;

  return {
    label,
    slug: encodeURIComponent(raw),
  };
}

/**
 * categoryを「表示名(label)」と「URL用slug」に正規化
 * - 文字列 / オブジェクト / 配列 すべて対応
 */
export function normalizeCategories(
  input: MicroCMSCategory
): { label: string; slug: string }[] {
  if (!input) return [];

  if (typeof input === "string") {
    const s = input.trim();
    return s ? [{ label: s, slug: encodeURIComponent(s) }] : [];
  }

  if (Array.isArray(input)) {
    const out: { label: string; slug: string }[] = [];

    for (const item of input) {
      if (!item) continue;

      if (typeof item === "string") {
        const s = item.trim();
        if (!s) continue;
        out.push({ label: s, slug: encodeURIComponent(s) });
      } else {
        const n = normalizeCategoryItem(item);
        if (n) out.push(n);
      }
    }

    const map = new Map<string, { label: string; slug: string }>();
    for (const c of out) {
      if (!map.has(c.slug)) map.set(c.slug, c);
    }

    return [...map.values()];
  }

  const n = normalizeCategoryItem(input);
  return n ? [n] : [];
}

/**
 * 旧コード互換: 先頭1件だけ返す
 */
export function normalizeCategory(
  input: MicroCMSCategory
): { label: string; slug: string } | null {
  const list = normalizeCategories(input);
  return list.length > 0 ? list[0] : null;
}

/**
 * 本文HTMLを返す（body優先、なければcontent）
 */
export function getArticleBodyHtml(article: MicroCMSArticle | null): string {
  if (!article) return "";
  return (article.body ?? article.content ?? "").toString();
}

// ---------- API ----------

export async function fetchAllArticles(): Promise<MicroCMSArticle[]> {
  if (!client) return [];

  const limit = 100;
  let offset = 0;
  let all: MicroCMSArticle[] = [];

  while (true) {
    const res = await client.getList<MicroCMSArticle>({
      endpoint: endpointArticles,
      queries: {
        limit,
        offset,
        orders: "-publishedAt",
      },
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
      endpoint: endpointArticles,
      contentId: id,
    });
    return res ?? null;
  } catch {
    return null;
  }
}