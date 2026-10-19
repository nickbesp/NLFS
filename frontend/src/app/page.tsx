import Link from "next/link";

import ComingSoon from "@/components/ComingSoon";
import Icon from "@/components/Icon";
import ProgressBar from "@/components/ProgressBar";
import { api } from "@/lib/api";
import { averageAccuracy, levelProgress, nextTopic, quizQuestionCount } from "@/lib/dashboard";
import { getT } from "@/lib/i18n/server";
import { LEVELS } from "@/lib/types";

export default async function Dashboard() {
  const [t, stats, topics, history] = await Promise.all([getT(), api.stats(), api.topics(), api.history()]);

  const next = nextTopic(topics);
  const nextDetail = next ? await api.topic(next.id) : null;
  const level = next?.level ?? null;
  const progress = level ? levelProgress(topics, level) : null;
  const accuracy = averageAccuracy(history);
  const quizCount = quizQuestionCount(nextDetail?.cards.length ?? 0);

  const topicHref = next ? `/theory/${next.level}/${next.id}` : "/theory";
  const quizHref = next ? `/quizzes?topic=${next.id}` : "/quizzes";

  return (
    <div className="page dashboard">
      {/* ---------- Top bar ---------- */}
      <div className="topbar">
        <div className="search">
          <ComingSoon id="search" compact />
        </div>
        <div className="level-chips">
          <span>{t("dash.levelLabel")}</span>
          {LEVELS.map((l) => (
            <Link key={l} href={`/theory/${l}`} className={`chip${l === level ? " active" : ""}`}>
              {l}
            </Link>
          ))}
        </div>
        <ComingSoon id="notifications" compact />
        <Link href="/flashcards" className="button">
          <Icon name="play_arrow" filled />
          {t("dash.dailyPractice")}
        </Link>
      </div>

      {/* ---------- Welcome hero ---------- */}
      <section className="panel hero">
        <div className="hero-grid">
          <div>
            {level && (
              <span className="pill pill-green">
                <Icon name="eco" />
                {t("dash.activeTrack", { level })}
              </span>
            )}
            <h1>{t("dash.hello", { name: "Nikita" })}</h1>
            <p>{next ? t("dash.heroSubtitle") : t("dash.allDoneHint")}</p>
            <ComingSoon id="streak" compact />
          </div>
          <div className="hero-side">
            <ComingSoon id="xp">
              <div className="stat">
                <div className="stat-label">XP</div>
                <ProgressBar percent={70} />
              </div>
            </ComingSoon>
            <Link href={topicHref} className="button">
              <Icon name={next ? "play_circle" : "task_alt"} />
              {next ? t("dash.continue", { topic: next.title }) : t("dash.allDone")}
            </Link>
          </div>
        </div>
      </section>

      {/* ---------- Main study plan ---------- */}
      <section>
        <div className="section-head">
          <div>
            <span className="eyebrow">{t("dash.planEyebrow")}</span>
            <h2>{level ? t("dash.planTitle", { level }) : t("nav.theory")}</h2>
          </div>
          <Link href={level ? `/theory/${level}` : "/theory"} className="text-link">
            {t("dash.viewSyllabus")}
            <Icon name="arrow_forward" />
          </Link>
        </div>

        <div className="panel">
          {topics.length === 0 ? (
            <p className="empty-state">
              <Icon name="hourglass_empty" />
              {t("dash.noTopics")}
            </p>
          ) : !next || !nextDetail || !progress ? (
            <p className="empty-state">
              <Icon name="task_alt" />
              {t("dash.allDoneHint")}
            </p>
          ) : (
            <>
              <div className="unit-head">
                <div className="unit-title">
                  <span className="unit-icon">
                    <Icon name="menu_book" />
                  </span>
                  <div>
                    <div className="unit-meta">
                      <span className="badge">{next.level}</span>
                      <span>{t("dash.lessonsDone", { done: progress.done, total: progress.total })}</span>
                    </div>
                    <h3>{next.title}</h3>
                  </div>
                </div>
                <div className="unit-progress">
                  <div>
                    <div className="percent">{progress.percent}%</div>
                    <span className="hint">{t("dash.levelProgress")}</span>
                  </div>
                  <ProgressBar percent={progress.percent} label={t("dash.levelProgress")} />
                </div>
              </div>

              <div className="modules">
                <Link href={topicHref} className="module">
                  <div className="module-top">
                    <span className="pill pill-green">
                      <Icon name="auto_stories" />
                      {t("dash.moduleTheory")}
                    </span>
                  </div>
                  <h4>{nextDetail.title}</h4>
                  <p>{t("dash.theoryDesc")}</p>
                  <span className="module-go">
                    <Icon name="arrow_forward" />
                  </span>
                </Link>

                {quizCount > 0 ? (
                  <Link href={quizHref} className="module">
                    <div className="module-top">
                      <span className="pill pill-green">
                        <Icon name="quiz" />
                        {t("dash.moduleQuiz")}
                      </span>
                      <span>{t("dash.questions", { count: quizCount })}</span>
                    </div>
                    <h4>{t("quiz.practice", { topic: nextDetail.title })}</h4>
                    <p>{t("dash.quizDesc")}</p>
                    <span className="module-go">
                      <Icon name="play_arrow" />
                    </span>
                  </Link>
                ) : (
                  <div className="module muted-module">
                    <div className="module-top">
                      <span className="pill">
                        <Icon name="quiz" />
                        {t("dash.moduleQuiz")}
                      </span>
                    </div>
                    <h4>{t("quiz.practice", { topic: nextDetail.title })}</h4>
                    <p>{t("dash.noQuiz")}</p>
                  </div>
                )}

                <Link href={topicHref} className="module">
                  <div className="module-top">
                    <span className="pill pill-amber">
                      <Icon name="translate" />
                      {t("dash.moduleVocab")}
                    </span>
                    <span>{t("dash.words", { count: nextDetail.cards.length })}</span>
                  </div>
                  <h4>{nextDetail.cards.slice(0, 3).map((c) => c.spanish).join(", ") || nextDetail.title}</h4>
                  <p>{t("dash.vocabDesc")}</p>
                  <span className="module-go">
                    <Icon name="visibility" />
                  </span>
                </Link>
              </div>
            </>
          )}
        </div>
      </section>

      {/* ---------- Recommended practice ---------- */}
      <section>
        <div className="section-head">
          <h2>{t("dash.recommendedTitle")}</h2>
        </div>
        <div className="rec-grid">
          <div className="panel rec-card">
            <div className="rec-top">
              <span className="rec-icon">
                <Icon name="style" />
              </span>
              {stats.cards_due > 0 && <span className="pill pill-amber">{t("dash.srsUrgent")}</span>}
            </div>
            <h3>{t("dash.srsTitle")}</h3>
            <p>{stats.cards_due > 0 ? t("dash.srsDue", { count: stats.cards_due }) : t("dash.srsNone")}</p>
            {stats.cards_due > 0 && (
              <Link href="/flashcards" className="button block">
                <Icon name="play_arrow" filled />
                {t("dash.srsButton")}
              </Link>
            )}
          </div>

          <div className="panel rec-card">
            <div className="rec-top">
              <span className="rec-icon amber">
                <Icon name="menu_book" />
              </span>
            </div>
            <span className="eyebrow">{t("dash.theoryBlockEyebrow")}</span>
            <h3>{next ? next.title : t("dash.allDone")}</h3>
            <p>{next ? t("dash.theoryDesc") : t("dash.allDoneHint")}</p>
            <Link href={topicHref} className="button secondary block">
              <Icon name="auto_stories" />
              {t("dash.readTheory")}
            </Link>
          </div>

          <div className="panel rec-card">
            <div className="rec-top">
              <span className="rec-icon">
                <Icon name="assignment" />
              </span>
              {quizCount > 0 && <span className="pill">{t("dash.questions", { count: quizCount })}</span>}
            </div>
            <span className="eyebrow">{t("dash.quickQuizEyebrow")}</span>
            <h3>{next ? t("quiz.practice", { topic: next.title }) : t("quiz.title")}</h3>
            <p>{t("dash.quizDesc")}</p>
            <Link href={quizCount > 0 ? quizHref : "/quizzes"} className="button secondary block">
              <Icon name="play_circle" />
              {t("dash.startQuiz")}
            </Link>
          </div>
        </div>
      </section>

      {/* ---------- Metrics + exam ---------- */}
      <section className="metrics-grid">
        <div className="panel metrics">
          <div className="metrics-head">
            <div>
              <h2>{t("dash.metricsTitle")}</h2>
              <p>{t("dash.metricsSubtitle")}</p>
            </div>
            <ComingSoon id="weeklyTime" compact />
          </div>

          <div className="stat-tiles">
            <div className="stat">
              <div className="stat-label">{t("dash.vocabInDeck")}</div>
              <div className="stat-value">{stats.cards_total}</div>
              <div className="stat-hint">{t("dash.vocabInDeckHint")}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("dash.testsDone")}</div>
              <div className="stat-value">{stats.quizzes_taken}</div>
              <div className="stat-hint">{t("dash.testsDoneHint")}</div>
            </div>
            <div className="stat">
              <div className="stat-label">{t("dash.accuracy")}</div>
              <div className="stat-value">{accuracy === null ? "—" : `${accuracy}%`}</div>
              <div className="stat-hint">{t("dash.accuracyHint")}</div>
            </div>
          </div>

          <div className="metrics-charts">
            <ComingSoon id="studyHours">
              <div className="fake-bars">
                {[30, 55, 70, 45, 85, 10, 10].map((h, i) => (
                  <span key={i} style={{ height: `${h}%` }} />
                ))}
              </div>
            </ComingSoon>
            <ComingSoon id="cefrSkills">
              <div className="fake-skills">
                {[78, 70, 65].map((p) => (
                  <ProgressBar key={p} percent={p} />
                ))}
              </div>
            </ComingSoon>
          </div>
        </div>

        <div className="panel exam-card">
          <span className="eyebrow">{t("dash.examEyebrow")}</span>
          <ComingSoon id="mockExam">
            <div className="fake-skills">
              <ProgressBar percent={80} />
              <ProgressBar percent={40} />
            </div>
          </ComingSoon>
        </div>
      </section>

      {/* ---------- Culture ---------- */}
      <section className="panel">
        <span className="eyebrow">{t("dash.cultureEyebrow")}</span>
        <ComingSoon id="cultureTip" />
      </section>
    </div>
  );
}
