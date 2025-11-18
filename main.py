import dotenv
import logging

from jobsidian.cli import main


if __name__ == "__main__":
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
