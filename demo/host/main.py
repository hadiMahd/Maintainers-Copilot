import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logging.getLogger(__name__).info("demo_host: not implemented")
raise SystemExit(0)
