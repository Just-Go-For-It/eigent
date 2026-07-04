"""Sentiment sub-agent.

Scores news headlines into a bounded conviction signal in [-1, 1]. Default is a deterministic
lexicon scorer (no deps, no network) so it works offline and in CI. Optionally, an LLM can be
used for nuance when one is configured. Like fundamentals, sentiment only *nudges* the bull/bear
debate — it never bypasses RiskGuard.
"""
from __future__ import annotations

import re

POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "growth", "grow", "upgrade",
    "upgraded", "record", "profit", "profits", "gain", "gains", "rally", "rallies",
    "strong", "outperform", "bullish", "raise", "raised", "tops", "wins", "approval",
    "breakthrough", "expands", "rebound",
}
NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "drop", "drops", "downgrade", "downgraded",
    "loss", "losses", "lawsuit", "probe", "weak", "cut", "cuts", "decline", "declines",
    "fraud", "bankruptcy", "recall", "warns", "warning", "slump", "bearish", "halts",
    "investigation", "default", "layoffs", "slashes",
}

_WORD = re.compile(r"[a-z']+")


class SentimentAnalyzer:
    def __init__(self, llm=None, use_llm: bool = False):
        self.llm = llm
        self.use_llm = use_llm and llm is not None

    def score(self, headlines: list[str]) -> tuple[float, str]:
        if not headlines:
            return 0.0, "sentiment: neutral (no news)"
        if self.use_llm:
            return self._score_llm(headlines)
        return self._score_lexicon(headlines)

    def _score_lexicon(self, headlines: list[str]) -> tuple[float, str]:
        pos = neg = 0
        for h in headlines:
            for w in _WORD.findall(h.lower()):
                if w in POSITIVE:
                    pos += 1
                elif w in NEGATIVE:
                    neg += 1
        total = pos + neg
        if total == 0:
            return 0.0, f"sentiment: neutral (0 cues across {len(headlines)} headlines)"
        score = max(-1.0, min(1.0, (pos - neg) / total))
        label = "bullish" if score > 0.15 else "bearish" if score < -0.15 else "mixed"
        return score, f"sentiment: {label} ({pos}+/{neg}- across {len(headlines)} headlines)"

    def _score_llm(self, headlines: list[str]) -> tuple[float, str]:
        out = self.llm.complete(
            system="You are a financial news sentiment classifier. Reply with one word: "
            "bullish, bearish, or neutral.",
            prompt="Headlines:\n- " + "\n- ".join(headlines),
        )
        low = out.lower()
        if "bull" in low:
            return 0.6, f"sentiment: bullish (llm) over {len(headlines)} headlines"
        if "bear" in low:
            return -0.6, f"sentiment: bearish (llm) over {len(headlines)} headlines"
        return 0.0, f"sentiment: neutral (llm) over {len(headlines)} headlines"
