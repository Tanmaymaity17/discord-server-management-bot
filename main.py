"""Entry point:  python main.py"""
from bot import config
from bot.client import ServerBot


def main() -> None:
    ServerBot().run(config.TOKEN)


if __name__ == "__main__":
    main()
