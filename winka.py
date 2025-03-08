import os
import time
import requests
import asyncio
from tkinter import Tk, Label, Entry, Button, StringVar, messagebox
from playwright.async_api import async_playwright
import re
from concurrent.futures import ThreadPoolExecutor

# Constants
SCRIPT_DIR = r"C:\\Users\\spidereyelamb\\Desktop\\winka"
DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "downloads")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "tiktok_video_ids.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# TikTok Video Downloader with Updated Logic
def download_video_by_id(video_id, title=None):
    """
    Download the TikTok video using the savetik.net API.
    """
    api_url = f"https://savetik.net/api/action?url=https%3A%2F%2Fm.tiktok.com%2Fv%2F{video_id}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract the download link
        video_link = data.get("video_link")
        if not video_link:
            print(f"✗ Error: No video link found for video ID {video_id}.")
            return None

        # Construct the full download URL
        download_url = f"https://savetik.net{video_link}"
        filename = title if title and title != "Unknown Title" else data.get("filename", f"video_{video_id}.mp4")
        filename = f"{re.sub(r'[\\/:*?"<>|]', '', filename)}.mp4"  # Remove invalid characters for filenames
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        print(f"Downloading video from {download_url}")
        video_response = requests.get(download_url, headers=headers, stream=True)
        video_response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=64 * 1024):  # Increased chunk size for faster downloads
                if chunk:
                    f.write(chunk)

        print(f"✓ Video downloaded successfully: {filepath}")
        return filepath

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to download video ID {video_id}. Error: {e}")
        return None

# Fetch TikTok Title from oEmbed
def fetch_tiktok_title(video_id):
    """
    Fetch the title of the TikTok video using the oEmbed API.
    """
    oembed_url = f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@tiktok/video/{video_id}"
    try:
        response = requests.get(oembed_url)
        response.raise_for_status()
        data = response.json()
        title = data.get("title", "Unknown Title")
        return title
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to fetch title for video ID {video_id}. Error: {e}")
        return "Unknown Title"

# TikTok Video ID Extractor
def extract_video_ids(profile_url, output_file):
    async def _extract_video_ids():
        video_ids = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            print(f"Navigating to TikTok profile: {profile_url}")
            await page.goto(profile_url)
            await page.wait_for_load_state("networkidle", timeout=60000)
            await page.evaluate("() => window.scrollBy(0, window.innerHeight)")
            video_elements = await page.query_selector_all("div[data-e2e='user-post-item'] a")
            for video_element in video_elements:
                video_url = await video_element.get_attribute("href")
                if video_url and "/video/" in video_url:
                    video_id = video_url.split("/video/")[-1].split("?")[0]
                    if video_id not in video_ids:
                        video_ids.append(video_id)
                        with open(output_file, "a") as file:
                            file.write(video_id + "\n")
            await browser.close()
        print(f"Extracted {len(video_ids)} video IDs. Saved to {output_file}.")
    asyncio.run(_extract_video_ids())

# Parallel Video Download
def process_videos(video_ids):
    def download(video_id):
        print(f"Processing video ID: {video_id}")

        # Fetch title using oEmbed API
        title = fetch_tiktok_title(video_id)
        print(f"Video Title: {title}")

        # Attempt to download the video
        video_path = download_video_by_id(video_id, title=title)
        if video_path:
            print(f"Downloaded: {video_path}")
        else:
            print(f"Failed to download video ID: {video_id}")

    with ThreadPoolExecutor(max_workers=10) as executor:  # Increased max_workers for parallel execution
        executor.map(download, video_ids)

# Responsive GUI Implementation
def start_gui():
    def on_extract_ids():
        profile_url = profile_url_var.get().strip()
        if not profile_url:
            messagebox.showerror("Input Error", "TikTok profile URL is required.")
            return
        try:
            extract_video_ids(profile_url, OUTPUT_FILE)
            messagebox.showinfo("Success", f"Video IDs extracted and saved to {OUTPUT_FILE}.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_submit():
        try:
            with open(OUTPUT_FILE, "r") as file:
                video_ids = file.read().splitlines()
            if not video_ids:
                messagebox.showerror("Input Error", "No video IDs found. Please extract video IDs first.")
                return

            process_videos(video_ids)

            messagebox.showinfo("Success", "All videos processed.")
        except FileNotFoundError:
            messagebox.showerror("Error", "Video ID file not found. Please extract video IDs first.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    root = Tk()
    root.title("TikTok Downloader")

    root.geometry("1024x768")
    root.minsize(800, 600)
    root.resizable(True, True)

    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=3)
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    Label(root, text="TikTok Profile URL").grid(row=0, column=0, padx=10, pady=5, sticky="e")
    profile_url_var = StringVar()
    Entry(root, textvariable=profile_url_var).grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    Button(root, text="Extract Video IDs", command=on_extract_ids).grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

    Button(root, text="Download All Videos", command=on_submit).grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")

    root.mainloop()

if __name__ == "__main__":
    start_gui()
