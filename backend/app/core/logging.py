import logging


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Не пишем строку лога на каждый апдейт — в ней ID пользователей
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
