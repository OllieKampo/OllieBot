from .bot import OllieBot
from .config import TwitchConfig


def main() -> None:
    config = TwitchConfig.from_env()
    bot = OllieBot(config)
    bot.run()


if __name__ == "__main__":
    main()
