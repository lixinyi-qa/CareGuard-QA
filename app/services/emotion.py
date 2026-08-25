from dataclasses import dataclass


DISCLAIMER = "结果仅用于日常情绪关怀，不构成医疗诊断或治疗建议。"

POSITIVE_WORDS = {
    "开心",
    "高兴",
    "幸福",
    "舒服",
    "满意",
    "顺利",
    "期待",
    "安心",
    "感谢",
    "谢谢",
    "不错",
    "很好",
    "快乐",
    "有精神",
    "喜欢",
}
NEGATIVE_WORDS = {
    "难过",
    "伤心",
    "孤独",
    "焦虑",
    "害怕",
    "担心",
    "失眠",
    "痛苦",
    "生气",
    "糟糕",
    "没意思",
    "没人陪",
    "不舒服",
    "烦",
}
HIGH_RISK_PHRASES = {
    "不想活",
    "活着没意思",
    "结束生命",
    "伤害自己",
    "自杀",
    "永远离开",
}
NEGATIONS = ("不", "没", "没有", "并不", "不太")


@dataclass(frozen=True)
class EmotionResult:
    label: str
    confidence: int
    positive_hits: tuple[str, ...]
    negative_hits: tuple[str, ...]
    is_high_risk: bool


def _is_negated(text: str, index: int) -> bool:
    prefix = text[max(0, index - 3) : index]
    return any(prefix.endswith(word) for word in NEGATIONS)


def classify_emotion(text: str) -> EmotionResult:
    normalized = "".join(text.lower().split())
    positive: list[str] = []
    negative: list[str] = []

    for word in POSITIVE_WORDS:
        start = normalized.find(word)
        if start >= 0:
            (negative if _is_negated(normalized, start) else positive).append(word)

    for word in NEGATIVE_WORDS:
        start = normalized.find(word)
        if start >= 0:
            (positive if _is_negated(normalized, start) else negative).append(word)

    score = len(positive) - len(negative)
    if score > 0:
        label = "positive"
    elif score < 0:
        label = "negative"
    else:
        label = "neutral"

    evidence = len(positive) + len(negative)
    confidence = min(95, 55 + evidence * 12) if evidence else 55
    high_risk = any(phrase in normalized for phrase in HIGH_RISK_PHRASES)
    if high_risk:
        label = "negative"
        confidence = max(confidence, 90)

    return EmotionResult(
        label=label,
        confidence=confidence,
        positive_hits=tuple(sorted(positive)),
        negative_hits=tuple(sorted(negative)),
        is_high_risk=high_risk,
    )


def emotion_display(label: str) -> str:
    return {"positive": "积极", "neutral": "中性", "negative": "消极"}.get(label, "中性")
