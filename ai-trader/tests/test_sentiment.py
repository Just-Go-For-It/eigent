from src.agents.sentiment import SentimentAnalyzer


def test_empty_headlines_neutral():
    s, label = SentimentAnalyzer().score([])
    assert s == 0.0
    assert "neutral" in label


def test_positive_headlines_bullish():
    s, label = SentimentAnalyzer().score(
        ["Company beats earnings and raises guidance", "Stock surges to record high"]
    )
    assert s > 0
    assert "bullish" in label


def test_negative_headlines_bearish():
    s, label = SentimentAnalyzer().score(
        ["Company misses estimates amid lawsuit", "Shares plunge after downgrade"]
    )
    assert s < 0
    assert "bearish" in label


def test_score_is_bounded():
    s, _ = SentimentAnalyzer().score(["surge surge beats record profit rally gains" * 3])
    assert -1.0 <= s <= 1.0


def test_no_cue_words_neutral():
    s, _ = SentimentAnalyzer().score(["Company schedules annual meeting for shareholders"])
    assert s == 0.0
