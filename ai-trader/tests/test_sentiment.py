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


# ---- LLM mode (end-to-end wiring, tested with a fake LLM) ----
class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def complete(self, system, prompt, model=None):
        self.calls += 1
        return self.reply


def test_llm_mode_bullish():
    s, label = SentimentAnalyzer(llm=FakeLLM("Bullish"), use_llm=True).score(["anything"])
    assert s == 0.6 and "bullish" in label


def test_llm_mode_bearish():
    s, label = SentimentAnalyzer(llm=FakeLLM("this reads bearish to me"), use_llm=True).score(["x"])
    assert s == -0.6 and "bearish" in label


def test_llm_mode_neutral():
    s, _ = SentimentAnalyzer(llm=FakeLLM("neutral"), use_llm=True).score(["x"])
    assert s == 0.0


def test_llm_not_called_when_no_headlines():
    llm = FakeLLM("bullish")
    s, _ = SentimentAnalyzer(llm=llm, use_llm=True).score([])
    assert s == 0.0 and llm.calls == 0  # short-circuits before spending tokens


def test_use_llm_ignored_without_llm():
    # use_llm=True but no llm provided -> falls back to lexicon
    analyzer = SentimentAnalyzer(llm=None, use_llm=True)
    assert analyzer.use_llm is False
