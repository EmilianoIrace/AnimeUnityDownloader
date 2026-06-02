"""Module to download anime episodes from a given AnimeUnity URL.

It extracts the anime ID, formats the anime name, retrieves episode IDs and
URLs, and downloads episodes concurrently.

Usage:
    - Run the script with the URL of the anime page as a command-line argument.
    - It will create a directory structure in the 'Downloads' folder based on
      the anime name where each episode will be downloaded.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import time
from argparse import ArgumentParser
from collections.abc import Callable
from pathlib import Path

import requests
from rich.live import Live

from helpers.config import prepare_headers
from helpers.crawler.crawler import Crawler
from helpers.crawler.crawler_utils import extract_download_link
from helpers.download_utils import (
    get_episode_filename,
    get_chunk_size,
    run_in_parallel,
    save_file_with_progress,
)
from helpers.general_utils import (
    clear_terminal,
    create_download_directory,
    fetch_page,
    fetch_page_httpx,
)
from helpers.progress_utils import create_progress_bar, create_progress_table

ProgressCallback = Callable[[dict], None]


def download_episode(
    download_link: str,
    download_path: str,
    task_info: tuple,
    retries: int = 4,
    episode_index: int = 0,
    total_episodes: int = 0,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Download an episode from the download link and provides progress updates."""
    for attempt in range(retries):
        try:
            headers = prepare_headers()
            response = requests.get(
                download_link, stream=True, headers=headers, timeout=10,
            )
            response.raise_for_status()

            filename = get_episode_filename(download_link)
            final_path = Path(download_path) / filename

            if progress_callback:
                file_size = int(response.headers.get("Content-Length", -1))
                chunk_size = get_chunk_size(file_size) if file_size > 0 else 1024 * 256
                total_downloaded = 0
                with Path(final_path).open("wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            if file_size > 0:
                                pct = round((total_downloaded / file_size) * 100, 1)
                                progress_callback({
                                    "event": "episode_progress",
                                    "episode": episode_index,
                                    "total": total_episodes,
                                    "percent": pct,
                                })
                progress_callback({
                    "event": "episode_done",
                    "episode": episode_index,
                    "total": total_episodes,
                })
            else:
                save_file_with_progress(response, final_path, task_info)
            break

        except requests.RequestException:
            if attempt < retries - 1:
                delay = 10 * (attempt + 1) + random.uniform(0, 2)  # noqa: S311
                time.sleep(delay)


def process_video_url(
    video_url: str,
    download_path: str,
    task_info: tuple,
    episode_index: int = 0,
    total_episodes: int = 0,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Process an embed URL to extract episode download links."""
    soup = fetch_page(video_url)
    script_items = soup.find_all("script")
    download_link = extract_download_link(script_items, video_url)
    download_episode(
        download_link,
        download_path,
        task_info,
        episode_index=episode_index,
        total_episodes=total_episodes,
        progress_callback=progress_callback,
    )


def _process_video_url_with_callback(
    video_url: str,
    download_path: str,
    task_info: tuple,
    episode_index: int,
    total_episodes: int,
    progress_callback: ProgressCallback,
) -> None:
    process_video_url(
        video_url,
        download_path,
        task_info,
        episode_index=episode_index,
        total_episodes=total_episodes,
        progress_callback=progress_callback,
    )


def download_anime(
    anime_name: str,
    video_urls: list[str],
    download_path: str,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Download episodes of a specified anime from provided video URLs."""
    if progress_callback:
        from concurrent.futures import ThreadPoolExecutor
        from helpers.config import DOWNLOAD_WORKERS

        total = len(video_urls)
        with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
            futures = [
                executor.submit(
                    _process_video_url_with_callback,
                    url,
                    download_path,
                    (),
                    idx + 1,
                    total,
                    progress_callback,
                )
                for idx, url in enumerate(video_urls)
            ]
            for f in futures:
                f.result()
    else:
        job_progress = create_progress_bar()
        progress_table = create_progress_table(anime_name, job_progress)
        with Live(progress_table, refresh_per_second=10):
            run_in_parallel(process_video_url, video_urls, job_progress, download_path)


async def process_anime_download(
    url: str,
    start_episode: int | None = None,
    end_episode: int | None = None,
    download_path: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Process the download of an anime from the specified URL."""
    soup = fetch_page_httpx(url)
    crawler = Crawler(url=url, start_episode=start_episode, end_episode=end_episode)
    video_urls = await crawler.collect_video_urls()

    try:
        anime_name = crawler.extract_anime_name(soup, url)
        resolved_path = create_download_directory(anime_name, base=download_path)
        download_anime(anime_name, video_urls, resolved_path, progress_callback)

    except ValueError as val_err:
        message = f"Value error: {val_err}"
        logging.exception(message)


def setup_parser() -> ArgumentParser:
    """Set up the argument parser for the anime download script."""
    parser = argparse.ArgumentParser(
        description="Download anime episodes from a given URL.",
    )
    parser.add_argument("url", help="The URL of the Anime series to download.")
    parser.add_argument(
        "--start", type=int, default=None, help="The starting episode number.",
    )
    parser.add_argument(
        "--end", type=int, default=None, help="The ending episode number.",
    )
    return parser


async def main() -> None:
    """Execute the script to download anime episodes from a given AnimeUnity URL."""
    clear_terminal()
    parser = setup_parser()
    args = parser.parse_args()
    await process_anime_download(
        args.url, start_episode=args.start, end_episode=args.end,
    )


if __name__ == "__main__":
    asyncio.run(main())
