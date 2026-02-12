import { getCollection } from "astro:content";
import { createClient } from "microcms-js-sdk";

export type ArticleItem = {
  id: string;
  title: string;
  description?: string;
  slug: string;
  tags: string[];
  levels: string[];
  quizUrl?: string;
  updatedAt?: string;
  bodyHtml?: string;
};

function env(name: string): string | undefined {
  return (import.meta as any).env?.[name] ?? process.env[name];
}

const SERVICE_DOMAIN = env("MICROCMS_SERVICE_DOMAIN");
const API_KEY = env("MICROCMS_API_KEY");
const ENDPOINT = env("MICROCMS_ENDPOINT") || "articles";

async function tryFetchFromMicroCMS(): Promise<ArticleItem[] | null> {
  if (!SERVICE_DOMAIN || !API_KEY) return null;

  try {
    const client = createClient({ serviceDomain: SERVICE_DOMAIN, apiKey: API_KEY });
    const list: any = await client.getList({ endpoint: ENDPOINT, queries: { limit: 100 } });
    const contents = (list?.contents ?? []) as any[];

    return contents.map((c) => ({
      id: String(c.id ?? c.slug ?? c.title),
      title: String(c.title ?? ""),
      description: c.description ? String(c.description) : undefined,
      slug: String(c.slug ?? c.id),
      tags: Array.isArray(c.tags) ? c.tags.map((t: any) => String(t)) : [],
      levels: Array.isArray(c.levels) ? c.levels.map((t: any) => String(t)) : [],
      quizUrl: c.quizUrl ? String(c.quizUrl) : undefined,
      updatedAt: c.updatedAt ? String(c.updatedAt) : undefined,
      bodyHtml: c.body ? String(c.body) : undefined,
    }));
  } catch {
    return null;
  }
}

export async function getAllArticles(): Promise<ArticleItem[]> {
  const remote = await tryFetchFromMicroCMS();
  if (remote && remote.length) return remote;

  const entries = await getCollection("articles");
  return entries.map((e) => ({
    id: e.id,
    title: e.data.title,
    description: e.data.description,
    slug: e.slug,
    tags: e.data.tags ?? [],
    levels: e.data.levels ?? [],
    quizUrl: e.data.quizUrl,
    updatedAt: e.data.updatedAt,
  }));
}
