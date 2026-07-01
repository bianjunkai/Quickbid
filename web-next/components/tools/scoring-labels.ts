"use client";

export type ScoringEvidenceRef = {
  page?: number | null;
  quote?: string;
  field_path?: string;
  label?: string;
};

export type ScoringChapterLike = {
  title?: string;
  subsections?: Array<{ title?: string }>;
  scoring_refs?: ScoringEvidenceRef[];
};

const PRICE_TERMS = ["报价", "价格", "投标报价", "开标一览", "分项报价"];

export function normalizeScoringLabel(value: string) {
  return String(value || "")
    .trim()
    .replace(/[；;]\s*(\d+(?:\.\d+)?)\s*$/, " $1分")
    .replace(/\s+(\d+(?:\.\d+)?)\s*$/, " $1分")
    .replace(/分分$/, "分");
}

export function normalizeMaybeScoringTitle(value: string) {
  if (!/(评分|得分|价格|报价)/.test(value)) return value;
  return normalizeScoringLabel(value);
}

export function isPriceScoringText(value: string) {
  return PRICE_TERMS.some((kw) => value.includes(kw));
}

export function chapterScoringText(chapter: ScoringChapterLike) {
  return [
    chapter.title || "",
    ...(chapter.subsections || []).map((s) => s.title || ""),
  ].join(" ");
}

export function scoringRefLabel(ref: ScoringEvidenceRef) {
  return normalizeScoringLabel(ref.label || ref.quote || "");
}

export function scoringRefMatchesChapter(
  ref: ScoringEvidenceRef,
  chapter: ScoringChapterLike
) {
  const chapterText = chapterScoringText(chapter);
  const refText = `${ref.label || ""} ${ref.quote || ""}`;
  if (!chapterText.trim() || !refText.trim()) return false;

  const refIsPrice = isPriceScoringText(refText);
  const chapterIsPrice = isPriceScoringText(chapterText);
  if (refIsPrice !== chapterIsPrice) return false;

  const chapterTokens = extractMeaningfulTokens(chapterText);
  const refTokens = extractMeaningfulTokens(refText);
  return chapterTokens.some((token) => refTokens.includes(token));
}

export function firstUsefulScoringRefLabel(chapter: ScoringChapterLike) {
  const refs = chapter.scoring_refs || [];
  const byPage = refs.find((r) => r.page);
  if (byPage) return `P.${byPage.page}`;

  const matched = refs.find((ref) => scoringRefMatchesChapter(ref, chapter));
  if (!matched) return "";
  return scoringRefLabel(matched).slice(0, 48) || "来源未定位";
}

function extractMeaningfulTokens(value: string) {
  const normalized = normalizeScoringLabel(value)
    .replace(/\d+(?:\.\d+)?\s*(分|%|元|万元)?/g, " ")
    .replace(/[^\u4e00-\u9fa5A-Za-z0-9]+/g, " ")
    .trim();
  const chunks = normalized.split(/\s+/).filter(Boolean);
  const tokens = new Set<string>();
  for (const chunk of chunks) {
    if (/^[A-Za-z0-9]+$/.test(chunk) && chunk.length >= 2) {
      tokens.add(chunk.toLowerCase());
      continue;
    }
    for (const word of chunk.match(/[\u4e00-\u9fa5]{2,}/g) || []) {
      if (!isWeakChineseToken(word)) tokens.add(word);
      for (let size = 2; size <= Math.min(4, word.length); size += 1) {
        for (let i = 0; i <= word.length - size; i += 1) {
          const token = word.slice(i, i + size);
          if (!isWeakChineseToken(token)) tokens.add(token);
        }
      }
    }
  }
  return Array.from(tokens);
}

function isWeakChineseToken(token: string) {
  return (
    token.length < 2 ||
    [
      "评分",
      "得分",
      "部分",
      "方案",
      "文件",
      "要求",
      "材料",
      "内容",
      "项目",
      "供应",
      "投标",
      "响应",
      "技术",
      "商务",
      "其他",
      "最高",
      "提供",
    ].includes(token)
  );
}
