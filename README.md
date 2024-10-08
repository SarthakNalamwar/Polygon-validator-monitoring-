﻿# Polygon-validator-monitoring-

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Docker Setup](#docker-setup)
7. [Monitoring Features](#monitoring-features)
8. [Alerting](#alerting)
9. [Troubleshooting](#troubleshooting)
10. [Version Information](#version-information)

## 1. Introduction

The Polygon Validator Monitoring Tool is a Python-based application designed to monitor the health and performance of a Polygon validator node. It checks various aspects of the node, including block heights, validator signatures, and account balances, and sends alerts via Telegram when issues are detected.

## 2. Prerequisites

- Python 3.7+
- Docker and Docker Compose (for containerized setup)
- Polygon validator node (Heimdall and Bor)
- Telegram Bot Token and Chat ID for alerting

## 3. Installation

1. Clone the repository containing the monitoring tool.
2. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 4. Configuration

The tool uses environment variables for configuration. You can set these in your system or use a `.env` file. Here are the available configuration options:

- `VALIDATOR_ADDRESS`: Your validator's address
- `LOCAL_HEIMDALL_API`: URL of your local Heimdall API (default: "http://127.0.0.1:26657")
- `REMOTE_HEIMDALL_API`: URL of the remote Heimdall API (default: "https://heimdall-api.polygon.technology")
- `LOCAL_BOR_API`: URL of your local Bor API (default: "http://127.0.0.1:8545")
- `REMOTE_BOR_API`: URL of the remote Bor API (default: "https://polygon-rpc.com")
- `INFURA_URL`: Your Infura URL for Ethereum mainnet
- `SIGNER_KEY`: Your validator's signer key
- `ETH_KEY_MIN_BALANCE`: Minimum balance threshold for alerting (in wei)
- `LOCAL_LAG_ALERT_AMOUNT`: Number of blocks behind to trigger a local lag alert
- `REMOTE_LAG_ALERT_AMOUNT`: Number of blocks behind to trigger a remote lag alert
- `ACCEPTABLE_CONSECUTIVE_MISSES`: Number of consecutive signature misses before alerting
- `CHECK_INTERVAL_SECONDS`: Interval between health checks
- `THROTTLE_INTERVAL_SECONDS`: Minimum time between repeated alerts
- `ACCEPTABLE_CONSECUTIVE_FLAKES`: Number of consecutive errors before alerting
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID for receiving alerts

## 5. Usage

To start the monitoring tool, run:

```bash
python monitoring_tool.py
```

The tool will continuously monitor your validator node and send alerts to the specified Telegram chat when issues are detected.

## 6. Docker Setup

A Docker Compose file is provided for easy setup of the Heimdall and Bor nodes. To use it:

1. Ensure Docker and Docker Compose are installed on your system.
2. Create a `docker-compose.yml` file with the following content:

```yaml
version: '3'
services:
  heimdall:
    image: linuxserver/heimdall:latest
    restart: always
    environment:
      - HEIMDALL_MODE=validator
      - HEIMDALL_RPC_LADDR=tcp://0.0.0.0:26657
    ports:
      - "26657:26657"

  bor:
    image: donbeave/bor:latest
    restart: always
    environment:
      - BOR_NETWORK_ID=137
      - BOR_CHAIN_ID=137
      - BOR_BOOTNODES=enode://0x...@bor-bootnode.polygon.technology:30303
    ports:
      - "8545:8545"
```

3. Start the containers:

```bash
docker-compose up -d
```

## 7. Monitoring Features

The tool monitors the following aspects of your validator node:

- Heimdall block height (local and remote)
- Bor block height (local and remote)
- Validator signatures in recent blocks
- Signer account balance

## 8. Alerting

Alerts are sent via Telegram when the following conditions are met:

- Local or remote Heimdall node is lagging
- Local or remote Bor node is lagging
- Multiple consecutive validator signatures are missed
- Signer account balance falls below the specified threshold
- Consecutive errors occur during the monitoring process

Alerts are throttled to prevent spam. The throttle interval can be configured using the `THROTTLE_INTERVAL_SECONDS` environment variable.

## 9. Troubleshooting

If you encounter issues:

1. Check that all required environment variables are set correctly.
2. Ensure your Polygon nodes (Heimdall and Bor) are running and accessible.
3. Verify that your Telegram bot token and chat ID are correct.
4. Check the console output for any error messages or unexpected behavior.

## 10. Version Information

Current version: 0.1.0

For the latest updates and information, please check the project repository.
