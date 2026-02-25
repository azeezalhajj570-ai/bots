import argparse

from group_manager_bot.main import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Group manager bot")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Enable test mode (apply anti-link rules to everyone, including admins and bots).",
    )
    args = parser.parse_args()
    main(test_mode=args.test)
