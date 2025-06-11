import argparse
import os
import asyncio
import random
import sys
import uuid
from miner.miner import Miner
import settings
import time
from loguru import logger


# Set PyTorch CUDA memory management environment variable to prevent fragmentation
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

logger.remove()  # Remove default handler
logger.add(sys.stderr, level="DEBUG")  # Add stderr handler for terminal output
if os.path.exists("miners.log"):
    try:
        os.remove("miners.log")
        logger.info("Removed existing miners.log file")
    except OSError as e:
        logger.error(f"Error removing miners.log: {e}")

logger.add(
    "miners.log",
    rotation="5 MB",  # Rotate at 5MB
    level="DEBUG",
    retention=1,  # Keep only latest log file
)


async def main(num_miners: int):
    miners = []
    startup_tasks = []
    for i in range(num_miners):
        hotkey = settings.MINER_HOTKEYS[i]
        device = f"cuda:{i}"
        logger.info(f"Launching miner {hotkey} on device {device}")
        miner = await Miner.create(
            wallet_name=settings.wallet_name,
            wallet_hotkey=hotkey,
            timeout=settings.TIMEOUT,
            n_layers=settings.N_LAYERS,
            device=device,
        )
        miners.append(miner)
        startup_tasks.append(miner.start())
    
    logger.info(f"Launching {len(startup_tasks)} miners in parallel")
    miner_tasks = await asyncio.gather(*startup_tasks)
    logger.info("All miners have been lauched")

    start = time.time()
    while True:
        await asyncio.sleep(random.random())
        print("...")
        if time.time() - start > settings.TIMEOUT:
            break
    return miners


# this is introduced in order to not break existing workflows
# and to allow flexibility for running remotely
async def main_docker(hotkey: str):
    miner = await Miner.create(
        wallet_name=settings.wallet_name,
        wallet_hotkey=settings.wallet_hotkey,
        timeout=settings.TIMEOUT,
        n_layers=settings.N_LAYERS,
        device="cuda:0",
    )
    task = await miner.start()
    await task


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env",
        type=str,
        default=os.getenv("ENV", "local"),
        help="Environment this is executing on",
    )
    parser.add_argument(
        "--miner_hotkey",
        type=str,
        default=os.getenv("MINER_HOTKEY", str(uuid.uuid4())),
        help="Miner hotkey",
    )
    args = parser.parse_args()

    if args.env != "local":
        logger.info(f"Launching {args.miner_hotkey} miner in docker")
        asyncio.run(main_docker(args.miner_hotkey))
    else:
        logger.info(f"Launching {len(settings.MINER_HOTKEYS)} miners")
        asyncio.run(main(len(settings.MINER_HOTKEYS)))
