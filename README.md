# OllieBot

A modular async Twitch bot for emote pyramid play and Twitch Helix integration.

## Overview

This repository hosts a Twitch bot built with `twitchio`, designed for modular extension and high-performance async operation. The bot tracks pyramid attempts and stores scores in SQLite.

## Requirements

- Python 3.14
- `uv`
- Twitch OAuth token and application credentials

## Setup

1. Install `uv` if it is not already available:
	```powershell
	python -m pip install --user uv
	```
2. Install and pin Python 3.14 for the repo:
	```powershell
	uv python install 3.14
	uv python pin 3.14
	```
3. Create the virtual environment:
	```powershell
	uv venv --python 3.14
	```
4. Create a `.env` file at the repository root:
	```env
	CLIENT_ID=...
	CLIENT_SECRET=...
	BOT_ID=...
	OWNER_ID=...
	APP_TOKEN=...
	BOT_ACCESS_TOKEN=...
	BOT_REFRESH_TOKEN=...
	TWITCH_CHANNELS=froggen
	```
	`BOT_ACCESS_TOKEN` and `BOT_REFRESH_TOKEN` are optional but recommended for managed user-token flows in TwitchIO v3.
5. Sync dependencies into the virtual environment:
	```powershell
	uv sync --group dev
	```
6. Run the bot:
	```powershell
	uv run olliebot
	```

## Development

- Run tests with:
  ```powershell
	uv run pytest
  ```
- Build a distributable package with:
  ```powershell
	uv build
  ```

## AWS Deployment

This bot is container-friendly and can be deployed to AWS Lightsail, ECS, or App Runner. The Docker image uses Python 3.14 and `uv` to create an isolated environment inside the container.
