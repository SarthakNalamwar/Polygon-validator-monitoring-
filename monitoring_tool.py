import asyncio
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp
import telegram
from web3 import Web3

# Configuration
CONFIG = {
    "VALIDATOR_ADDRESS": os.getenv("VALIDATOR_ADDRESS", ""),
    "LOCAL_HEIMDALL_API": os.getenv("LOCAL_HEIMDALL_API", "http://127.0.0.1:26657"),
    "REMOTE_HEIMDALL_API": os.getenv("REMOTE_HEIMDALL_API", "https://heimdall-api.polygon.technology"),
    "LOCAL_BOR_API": os.getenv("LOCAL_BOR_API", "http://127.0.0.1:8545"),
    "REMOTE_BOR_API": os.getenv("REMOTE_BOR_API", "https://polygon-rpc.com"),
    "INFURA_URL": os.getenv("INFURA_URL", ""),
    "SIGNER_KEY": os.getenv("SIGNER_KEY", "0x13dC53fa54E7d662Ff305b6C3EF95090c31dC576"),
    "ETH_KEY_MIN_BALANCE": Decimal(os.getenv("ETH_KEY_MIN_BALANCE", "300000000000000000")),
    "LOCAL_LAG_ALERT_AMOUNT": int(os.getenv("LOCAL_LAG_ALERT_AMOUNT", "5")),
    "REMOTE_LAG_ALERT_AMOUNT": int(os.getenv("REMOTE_LAG_ALERT_AMOUNT", "100")),
    "ACCEPTABLE_CONSECUTIVE_MISSES": int(os.getenv("ACCEPTABLE_CONSECUTIVE_MISSES", "3")),
    "CHECK_INTERVAL_SECONDS": int(os.getenv("CHECK_INTERVAL_SECONDS", "30")),
    "THROTTLE_INTERVAL_SECONDS": int(os.getenv("THROTTLE_INTERVAL_SECONDS", "300")),
    "ACCEPTABLE_CONSECUTIVE_FLAKES": int(os.getenv("ACCEPTABLE_CONSECUTIVE_FLAKES", "3")),
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", "7230019163:AAF1ZR1M7Zm03bKMxazJdaukHL3NWSFjY3o"),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", "-4543717139"),
}

VERSION = "0.1.0"

class ValidatorMonitor:
    """
    This class monitors the performance of a Polygon validator node by checking
    its block height, signature, and balance.
    """
    def __init__(self):
        self.consecutive_misses = 0
        self.consecutive_flakes = 0
        self.alert_throttle = {}
        self.bot = telegram.Bot(token=CONFIG["TELEGRAM_BOT_TOKEN"])

    async def send_alert(self, title, details, throttle_seconds=300, alert_key=None):
        """
        Sends an alert to the configured Telegram chat, with throttling to prevent
        spamming of repeated alerts.
        """
        alert_key = alert_key or f"{title}:{details}"
        now = datetime.now()

        if alert_key in self.alert_throttle:
            if now - self.alert_throttle[alert_key] < timedelta(seconds=throttle_seconds):
                return

        self.alert_throttle[alert_key] = now
        message = f"🚨 Alert: {title}\n\nDetails: {details}"
        await self.bot.send_message(chat_id=CONFIG["TELEGRAM_CHAT_ID"], text=message)

    async def fetch_json(self, url, method="GET", data=None):
        """
        Makes a request to a given URL and returns the parsed JSON response.
        """
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url) as response:
                    return await response.json()
            elif method == "POST":
                async with session.post(url, json=data) as response:
                    return await response.json()

    async def check_heimdall_height(self):
        """
        Checks and compares the block heights of the local and remote Heimdall nodes.
        Sends an alert if the local or remote node is significantly behind.
        """
        local_data = await self.fetch_json(f"{CONFIG['LOCAL_HEIMDALL_API']}/block")
        remote_data = await self.fetch_json(f"{CONFIG['REMOTE_HEIMDALL_API']}/checkpoints/count")

        local_height = int(local_data["result"]["block"]["header"]["height"])
        remote_height = int(remote_data["height"])

        print(f"Heimdall Block Heights: Local: {local_height}, Remote: {remote_height}")

        if remote_height - local_height > CONFIG["LOCAL_LAG_ALERT_AMOUNT"]:
            await self.send_alert("Local Heimdall node is lagging", f"Lag: {remote_height - local_height}")

        if local_height - remote_height > CONFIG["REMOTE_LAG_ALERT_AMOUNT"]:
            await self.send_alert("Remote Heimdall node is lagging", f"Lag: {local_height - remote_height}")

        return local_data, local_height

    async def check_bor_height(self):
        """
        Checks and compares the block heights of the local and remote Bor nodes.
        Alerts are sent if either node lags behind the other by a significant amount.
        """
        local_height = await self.fetch_json(CONFIG["LOCAL_BOR_API"], "POST", {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1})
        remote_height = await self.fetch_json(CONFIG["REMOTE_BOR_API"], "POST", {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1})

        local_height = int(local_height["result"], 16)
        remote_height = int(remote_height["result"], 16)

        print(f"Bor Block Heights: Local: {local_height}, Remote: {remote_height}")

        if remote_height - local_height > CONFIG["LOCAL_LAG_ALERT_AMOUNT"]:
            await self.send_alert("Local Bor node is lagging", f"Lag: {remote_height - local_height}")

        if local_height - remote_height > CONFIG["REMOTE_LAG_ALERT_AMOUNT"]:
            await self.send_alert("Remote Bor node is lagging", f"Lag: {local_height - remote_height}")

    async def check_validator_signature(self, heimdall_data):
        """
        Verifies whether the validator's signature is included in the latest block's
        precommits. Sends an alert if too many consecutive signatures are missed.
        """
        precommits = heimdall_data["result"]["block"]["last_commit"]["precommits"]
        found_signature = any(precommit and precommit["validator_address"].lower() == CONFIG["VALIDATOR_ADDRESS"].lower() for precommit in precommits if precommit)

        if found_signature:
            print("Validator precommit found.")
            self.consecutive_misses = 0
        else:
            self.consecutive_misses += 1
            print(f"Precommit missed. Consecutive misses: {self.consecutive_misses}")

        if self.consecutive_misses > CONFIG["ACCEPTABLE_CONSECUTIVE_MISSES"]:
            await self.send_alert("Missed Precommits", f"Consecutive misses: {self.consecutive_misses}")

    async def check_signer_balance(self):
        """
        Checks the balance of the validator's signer account and sends an alert if it
        falls below the minimum required threshold.
        """
        w3 = Web3(Web3.HTTPProvider(CONFIG["INFURA_URL"]))
        balance = w3.eth.get_balance(CONFIG["SIGNER_KEY"])

        print(f"Account balance: {balance} wei")
        if balance < CONFIG["ETH_KEY_MIN_BALANCE"]:
            await self.send_alert("Low ETH balance", f"Balance: {balance}")

    async def monitor(self):
        """
        Periodically checks the node health by calling various functions, and handles
        any errors or alerts accordingly.
        """
        print(f"Polygon Validator Monitor v{VERSION} running...")

        while True:
            try:
                print("\nPerforming node health check...")

                heimdall_data, _ = await self.check_heimdall_height()
                await self.check_bor_height()
                await self.check_validator_signature(heimdall_data)
                await self.check_signer_balance()

                self.consecutive_flakes = 0
                print("Health check successful!")

            except Exception as e:
                self.consecutive_flakes += 1
                print(f"Error encountered: {e}. Consecutive issues: {self.consecutive_flakes}")

                if self.consecutive_flakes >= CONFIG["ACCEPTABLE_CONSECUTIVE_FLAKES"]:
                    await self.send_alert("Error detected", str(e))

            await asyncio.sleep(CONFIG["CHECK_INTERVAL_SECONDS"])

if __name__ == "__main__":
    monitor = ValidatorMonitor()
    asyncio.run(monitor.monitor())
