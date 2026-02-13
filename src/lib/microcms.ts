import { createClient } from "microcms-js-sdk";

export const microcms =
  import.meta.env.MICROCMS_SERVICE_DOMAIN &&
  import.meta.env.MICROCMS_API_KEY
    ? createClient({
        serviceDomain: import.meta.env.MICROCMS_SERVICE_DOMAIN,
        apiKey: import.meta.env.MICROCMS_API_KEY,
      })
    : null;

export type Article = {
  id: string;
  title: string;
  description?: string;
  body: string;
  category?: string | string[] | { name?: string; title?: string } | any;
  publishedAt?: string;
};