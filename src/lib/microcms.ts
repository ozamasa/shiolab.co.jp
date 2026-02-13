// src/lib/microcms.ts
import { createClient, type MicroCMSClient } from "microcms-js-sdk";

const SERVICE_DOMAIN =
  import.meta.env.MICROCMS_SERVICE_DOMAIN || process.env.MICROCMS_SERVICE_DOMAIN;
const API_KEY =
  import.meta.env.MICROCMS_API_KEY || process.env.MICROCMS_API_KEY;

/**
 * microCMS クライアント（未設定なら null）
 * - Cloudflare Pages: 環境変数に MICROCMS_SERVICE_DOMAIN / MICROCMS_API_KEY を設定する
 */
export const microcms: MicroCMSClient | null =
  SERVICE_DOMAIN && API_KEY
    ? createClient({ serviceDomain: SERVICE_DOMAIN, apiKey: API_KEY })
    : null;

/**
 * microCMS 側の category が「文字列」「配列」「未設定」でも扱えるようにする
 */
export function normalizeCategory(input: unknown): string[] {
  if (!input) return [];
  if (Array.isArray(input)) {
    return input.map((v) => String(v).trim()).filter(Boolean);
  }
  return [String(input).trim()].filter(Boolean);
}

export type ArticleSummary = {
  id: string;
  title: string;
  description?: string;
  category?: string; // 既存ページ互換のため「1つ」に丸める
  categories?: string[]; // 必要なら将来使えるように残す
  date?: string;
};

/**
 * 記事一覧をまとめて取得（静的生成で使う）
 * - microCMS未設定でもビルドできるように [] を返す
 */
export async function fetchAllArticles(limit = 100): Promise<ArticleSummary[]> {
  if (!microcms) return [];

  const res = await microcms.getList({
    endpoint: "articles",
    queries: {
      limit,
      fields: "id,title,description,category,date",
    },
  });

  return res.contents.map((a: any) => {
    const cats = normalizeCategory(a.category);
    return {
      id: a.id,
      title: a.title,
      description: a.description,
      category: cats[0] ?? "",
      categories: cats,
      date: a.date,
    };
  });
}