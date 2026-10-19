import { setLang, setTheme } from "@/app/actions";
import Icon from "@/components/Icon";
import { LANG_NAMES } from "@/lib/i18n";
import { getPrefs, getT } from "@/lib/i18n/server";
import { LANGS, THEMES } from "@/lib/prefs";

const THEME_ICONS = { light: "light_mode", dark: "dark_mode" } as const;

export default async function SettingsPage() {
  const [{ theme, lang }, t] = await Promise.all([getPrefs(), getT()]);

  return (
    <div className="page narrow">
      <h1>{t("settings.title")}</h1>
      <p className="subtitle">{t("settings.subtitle")}</p>

      <section className="panel settings-section">
        <h2>{t("settings.appearance")}</h2>
        <p className="hint">{t("settings.appearanceHint")}</p>
        <div className="segmented" role="group" aria-label={t("settings.appearance")}>
          {THEMES.map((value) => (
            <form key={value} action={setTheme.bind(null, value)}>
              <button className={`segment${theme === value ? " active" : ""}`} aria-pressed={theme === value}>
                <Icon name={THEME_ICONS[value]} filled={theme === value} />
                {t(value === "light" ? "settings.light" : "settings.dark")}
              </button>
            </form>
          ))}
        </div>
      </section>

      <section className="panel settings-section">
        <h2>{t("settings.language")}</h2>
        <p className="hint">{t("settings.languageHint")}</p>
        <div className="segmented" role="group" aria-label={t("settings.language")}>
          {LANGS.map((value) => (
            <form key={value} action={setLang.bind(null, value)}>
              <button className={`segment${lang === value ? " active" : ""}`} aria-pressed={lang === value} lang={value}>
                {LANG_NAMES[value]}
              </button>
            </form>
          ))}
        </div>
      </section>
    </div>
  );
}
