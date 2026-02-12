import { defineCollection, z } from "astro:content";

const articles = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    tags: z.array(z.string()).default([]),
    levels: z.array(z.string()).default([]),
    quizUrl: z.string().optional(),
    updatedAt: z.string().optional()
  }),
});

export const collections = { articles };
