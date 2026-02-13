import { createClient } from "microcms-js-sdk";

const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;

export const microcms =
  serviceDomain && apiKey
    ? createClient({ serviceDomain, apiKey })
    : null;

export function normalizeCategory(category: any): string[] {
  if (!category) return [];

  if (Array.isArray(category)) {
    return category.map((c) =>
      typeof c === "string"
        ? c
        : c?.name || c?.title || ""
    ).filter(Boolean);
  }

  if (typeof category === "string") return [category];

  if (typeof category === "object") {
    return [category.name || category.title].filter(Boolean);
  }

  return [];
}