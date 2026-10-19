"use server";

// Server Actions: the only way the browser writes data. Each one calls FastAPI (or sets a preference
// cookie) from the Next.js server and then refreshes the server-rendered pages.
import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { api } from "@/lib/api";
import { LANG_COOKIE, parseLang, parseTheme, THEME_COOKIE } from "@/lib/prefs";
import type { QuizAnswer, QuizResult } from "@/lib/types";

export async function completeTopic(topicId: number): Promise<void> {
  await api.completeTopic(topicId);
  revalidatePath("/", "layout");
}

export async function reviewCard(cardId: number, quality: number): Promise<void> {
  await api.reviewCard(cardId, quality);
  revalidatePath("/", "layout");
}

export async function submitQuiz(topicId: number, answers: QuizAnswer[]): Promise<QuizResult> {
  const result = await api.submitQuiz(topicId, answers);
  revalidatePath("/", "layout");
  return result;
}

const PREF_COOKIE = { maxAge: 60 * 60 * 24 * 365, path: "/", sameSite: "lax" } as const;

export async function setTheme(theme: string): Promise<void> {
  (await cookies()).set(THEME_COOKIE, parseTheme(theme), PREF_COOKIE);
  revalidatePath("/", "layout");
}

export async function setLang(lang: string): Promise<void> {
  (await cookies()).set(LANG_COOKIE, parseLang(lang), PREF_COOKIE);
  revalidatePath("/", "layout");
}
