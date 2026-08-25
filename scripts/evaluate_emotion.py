import json
from collections import Counter
from pathlib import Path

from app.services.emotion import classify_emotion

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "tests" / "data" / "emotion_eval.json"
OUTPUT = ROOT / "outputs" / "ai-evaluation.json"
LABELS = ("positive", "neutral", "negative")


def safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    confusion = {expected: Counter() for expected in LABELS}
    failures = []
    risk_total = 0
    risk_found = 0

    for case in cases:
        result = classify_emotion(case["text"])
        confusion[case["label"]][result.label] += 1
        if result.label != case["label"] or result.is_high_risk != case["high_risk"]:
            failures.append(
                {
                    "id": case["id"],
                    "expected": case["label"],
                    "actual": result.label,
                    "expected_high_risk": case["high_risk"],
                    "actual_high_risk": result.is_high_risk,
                }
            )
        if case["high_risk"]:
            risk_total += 1
            risk_found += int(result.is_high_risk)

    metrics = {}
    for label in LABELS:
        true_positive = confusion[label][label]
        predicted_positive = sum(confusion[actual][label] for actual in LABELS)
        actual_positive = sum(confusion[label].values())
        precision = safe_ratio(true_positive, predicted_positive)
        recall = safe_ratio(true_positive, actual_positive)
        f1 = safe_ratio(2 * precision * recall, precision + recall)
        metrics[label] = {"precision": precision, "recall": recall, "f1": f1, "support": actual_positive}

    correct = sum(confusion[label][label] for label in LABELS)
    report = {
        "model": "CareGuard Chinese Emotion Baseline 1.0.0",
        "dataset": str(DATASET.relative_to(ROOT)),
        "cases": len(cases),
        "class_balance": dict(Counter(case["label"] for case in cases)),
        "accuracy": safe_ratio(correct, len(cases)),
        "macro_f1": round(sum(metrics[label]["f1"] for label in LABELS) / len(LABELS), 4),
        "per_class": metrics,
        "high_risk_recall": safe_ratio(risk_found, risk_total),
        "confusion_matrix": {label: dict(confusion[label]) for label in LABELS},
        "failures": failures,
        "limitations": [
            "This curated baseline set is small and is not clinical validation.",
            "Confidence is rule evidence strength, not calibrated probability.",
            "Sarcasm, dialects, and long mixed-emotion narratives need broader testing.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
