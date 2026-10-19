import type { Metadata } from "next";
import { Literata, Nunito_Sans } from "next/font/google";

import I18nProvider from "@/components/I18nProvider";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { getPrefs } from "@/lib/i18n/server";

import "@/styles/globals.css";

const literata = Literata({ subsets: ["latin", "cyrillic"], variable: "--font-headline", display: "swap" });
const nunito = Nunito_Sans({ subsets: ["latin", "cyrillic"], variable: "--font-body", display: "swap" });

export const metadata: Metadata = {
  title: "NLFS",
  description: "Nikita Learn Spanish",
};

/** Due-card badge for the sidebar. The shell must render even when the backend is down. */
async function dueCount(): Promise<number | null> {
  try {
    return (await api.stats()).cards_due;
  } catch {
    return null;
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Theme comes only from the cookie set in Settings, never from the OS.
  const [{ theme, lang }, due] = await Promise.all([getPrefs(), dueCount()]);

  return (
    <html lang={lang} data-theme={theme} className={`${literata.variable} ${nunito.variable}`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0..1,0&display=block"
        />
      </head>
      <body>
        <I18nProvider lang={lang}>
          <div className="shell">
            <Sidebar dueCount={due} />
            <main className="content">{children}</main>
          </div>
        </I18nProvider>
      </body>
    </html>
  );
}
