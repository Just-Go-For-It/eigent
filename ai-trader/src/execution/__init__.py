from .broker import Broker, Fill, PaperBroker, get_broker

__all__ = ["Broker", "Fill", "PaperBroker", "get_broker"]


def __getattr__(name):  # lazy optional backends (avoid importing heavy deps at package load)
    if name == "AlpacaMCPBroker":
        from .alpaca_mcp import AlpacaMCPBroker

        return AlpacaMCPBroker
    if name == "AlpacaBroker":
        from .alpaca_sdk import AlpacaBroker

        return AlpacaBroker
    raise AttributeError(name)
