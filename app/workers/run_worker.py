import asyncio
import logging

from app.workers.connection import rabbitmq
from app.workers.consumer import start_consumer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main():
    try:
        await start_consumer()
    finally:
        await rabbitmq.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped")