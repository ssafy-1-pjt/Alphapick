const rawBlockedTerms = [
  "씨발", "시발", "씹", "ㅅㅂ", "ㅆㅂ", "병신", "븅신", "ㅂㅅ", "개새끼", "개색기", "ㄱㅅㄲ",
  "좆", "존나", "ㅈㄴ", "ㅈ같", "지랄", "ㅈㄹ", "꺼져", "닥쳐", "등신", "호구", "빡대가리",
  "미친놈", "미친년", "쓰레기", "fuck", "shit", "bitch", "asshole",
];

function normalizeText(value = "") {
  return value
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}ㄱ-ㅎㅏ-ㅣ]+/gu, "")
    .replace(/\p{N}+/gu, "");
}

const blockedTerms = rawBlockedTerms.map(normalizeText);

export function containsProhibitedLanguage(value = "") {
  const normalized = normalizeText(value);
  return blockedTerms.some((term) => normalized.includes(term));
}

export const moderationNotice = "욕설·비속어는 사용할 수 없습니다. 투자 의견을 존중하는 표현으로 작성해 주세요.";
