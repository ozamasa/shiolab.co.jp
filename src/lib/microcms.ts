// src/lib/microcms.ts
import { createClient } from "microcms-js-sdk";

const serviceDomain = import.meta.env.MICROCMS_SERVICE_DOMAIN;
const apiKey = import.meta.env.MICROCMS_API_KEY;

export const microcms = (serviceDomain && apiKey)
  ? createClient({ serviceDomain, apiKey })
  : null;

export type Article = {
  id: string;
  title: string;
  description?: string;
  category?: string;
  publishedAt?: string;
  createdAt?: string;
  updatedAt?: string;
};