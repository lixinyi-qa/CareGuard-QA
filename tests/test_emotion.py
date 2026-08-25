import pytest

from app.services.emotion import DISCLAIMER, classify_emotion


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("今天和老朋友散步，我很开心", "positive"),
        ("今天按时吃饭，下午看了电视", "neutral"),
        ("最近总是失眠，心里很焦虑", "negative"),
        ("这件事并不糟糕，已经顺利解决", "positive"),
        ("今天不太开心", "negative"),
    ],
)
def test_three_class_emotion_baseline(text: str, expected: str):
    result = classify_emotion(text)
    assert result.label == expected
    assert 55 <= result.confidence <= 95


def test_high_risk_phrase_is_flagged_without_diagnosis():
    result = classify_emotion("我觉得活着没意思")
    assert result.label == "negative"
    assert result.is_high_risk is True
    assert result.confidence >= 90


def test_disclaimer_draws_medical_boundary():
    assert "不构成医疗诊断" in DISCLAIMER
