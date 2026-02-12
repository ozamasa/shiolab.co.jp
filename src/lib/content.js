import sample from '../content/sampleArticles.json';
import { createClient } from 'microcms-js-sdk';

function env(name) {
  // Astro build: import.meta.env is available; fallback to process.env
  return (import.meta?.env && (import.meta.env[name] ?? import.meta.env[`PUBLIC_${name}`])) ?? process.env[name] ?? process.env[`PUBLIC_${name}`];
}

const serviceDomain = env('MICROCMS_SERVICE_DOMAIN') || env('PUBLIC_MICROCMS_SERVICE_DOMAIN');
const apiKey = env('MICROCMS_API_KEY') || env('PUBLIC_MICROCMS_API_KEY');

const hasMicrocms = Boolean(serviceDomain && apiKey);

const client = hasMicrocms ? createClient({ serviceDomain, apiKey }) : null;

export function microcmsEnabled() {
  return hasMicrocms;
}

export async function getArticles() {
  if (!hasMicrocms) return sample.contents;
  const data = await client.get({ endpoint: 'articles' });
  return data.contents ?? [];
}

export async function getArticleSlugs() {
  const articles = await getArticles();
  return articles.map(a => a.slug).filter(Boolean);
}

export async function getArticleBySlug(slug) {
  const articles = await getArticles();
  return articles.find(a => a.slug === slug) || null;
}
