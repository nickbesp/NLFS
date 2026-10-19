// TO-DO LIST of features shown as "Coming soon" placeholders.
// Each entry is a part of the Terra design that has no data behind it yet.
// When a feature gets built, replace its <ComingSoon id="..."> with the real thing and delete it here.
// Names and "Needs:" notes live in the dictionaries under coming.<id>.name / coming.<id>.needs.
import type { MessageKey } from "./i18n/en.ts";

export const COMING_SOON = [
  { id: "search" }, // dashboard top bar
  { id: "notifications" }, // dashboard top bar
  { id: "profile" }, // sidebar card
  { id: "streak" }, // dashboard hero
  { id: "xp" }, // dashboard hero
  { id: "studyHours" }, // learning metrics
  { id: "weeklyTime" }, // learning metrics
  { id: "cefrSkills" }, // learning metrics
  { id: "mockExam" }, // dashboard card
  { id: "cultureTip" }, // dashboard card
] as const;

export type ComingSoonId = (typeof COMING_SOON)[number]["id"];

export function comingSoonKeys(id: ComingSoonId): { name: MessageKey; needs: MessageKey } {
  return { name: `coming.${id}.name`, needs: `coming.${id}.needs` };
}
