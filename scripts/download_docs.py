import os
import json
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Constants
BASE_URL = "https://web.archive.org/web/20230222120050/https://developer.qualcomm.com/hardware/apq-8016e/tools"
TEMP_DIR = "temp"
DOWNLOAD_MAP_FILE = os.path.join(TEMP_DIR, "download_map.json")

def get_wayback_url(url, timestamp="20230222120050"):
    """
    Constructs a Wayback Machine URL.
    Attempts to use the 'id_' modifier to get the raw file content, skipping the toolbar/wrapper.
    """
    if "web.archive.org" in url:
        return url

    # Check if it's a direct download link often redirected
    # We want to force the raw content
    return f"https://web.archive.org/web/{timestamp}id_/{url}"

def download_file(url, session):
    """Downloads a file from a URL. Returns the response object."""
    try:
        # We might need to chase redirects within the archive
        response = session.get(url, stream=True, allow_redirects=True)
        # Check status but don't raise yet, handle 404s gracefully in main
        return response
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None

def main():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    })

    print(f"Fetching main page: {BASE_URL}")
    try:
        response = session.get(BASE_URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching main page: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Find all download links
    links = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Extract original URL
        original_url = None
        match = re.search(r"/web/\d+/(https?://.+)", href)
        if match:
            original_url = match.group(1)
        elif href.startswith("http"):
             if "web.archive.org" not in href:
                 original_url = href

        if not original_url:
            continue

        if "developer.qualcomm.com/download/" in original_url:
             if original_url not in seen_urls:
                 path = urlparse(original_url).path
                 if path.lower().endswith(('.pdf', '.zip')):
                    links.append({"url": original_url, "text": a.get_text(strip=True)})
                    seen_urls.add(original_url)

    print(f"Found {len(links)} potential download links.")

    download_map = {}

    for i, link in enumerate(links):
        original_url = link["url"]
        dl_url = get_wayback_url(original_url)

        print(f"[{i+1}/{len(links)}] Downloading {original_url}...")

        response = download_file(dl_url, session)

        if response and response.status_code == 200:
            # Check for HTML wrapper (soft 404 or Wayback wrapper)
            content_start = b""
            try:
                content = response.content
                content_start = content[:100]
            except Exception:
                pass

            if b"<!DOCTYPE html>" in content_start or b"<html" in content_start:
                print(f"  Got HTML wrapper instead of file. Parsing...");
                # Wrapper handling logic
                try:
                    wrapper_soup = BeautifulSoup(content, "html.parser")
                    found_inner = False

                    # Common Wayback wrapper link: <a href="/web/.../http...">Impatient?</a>
                    for a in wrapper_soup.find_all("a", href=True):
                        # Heuristic: link that looks like the file or "Impatient?"
                        # We also check if the href simply contains the filename we expect
                        filename_part = os.path.basename(original_url.split('?')[0])

                        if (original_url in a["href"] or
                            filename_part in a["href"] or
                            "impatient" in a.get_text(strip=True).lower() or
                            "click here" in a.get_text(strip=True).lower()):

                             inner_url = a["href"]

                             # Fix relative URLs
                             if inner_url.startswith("/") and not inner_url.startswith("/web/"):
                                 # Assume relative to developer.qualcomm.com since that's where we are
                                 inner_url = urljoin("https://developer.qualcomm.com", inner_url)

                             # Ensure we use Wayback for this link
                             wb_inner_url = get_wayback_url(inner_url)

                             print(f"  Following wrapper link: {wb_inner_url}")
                             response = download_file(wb_inner_url, session)
                             if response and response.status_code == 200:
                                 content = response.content # update content
                                 if b"<!DOCTYPE html>" not in content[:100]:
                                    found_inner = True
                                    break

                    if not found_inner:
                        print("  Could not extract file from wrapper.")
                        continue
                except Exception as e:
                    print(f"  Error parsing wrapper: {e}")
                    continue

            # Determine extension
            content_type = response.headers.get("Content-Type", "")
            ext = ".pdf"
            if "zip" in content_type or original_url.lower().endswith(".zip"):
                ext = ".zip"

            filename = f"doc_{i:03d}{ext}"
            filepath = os.path.join(TEMP_DIR, filename)

            with open(filepath, "wb") as f:
                f.write(content)

            download_map[filename] = {
                "original_url": original_url,
                "download_url": dl_url,
                "link_text": link["text"]
            }
            print(f"  Saved to {filepath}")

            # Be nice to the archive
            time.sleep(1)
        else:
            print(f"  Failed to download. Status: {response.status_code if response else 'None'}")

    # Save the map
    with open(DOWNLOAD_MAP_FILE, "w") as f:
        json.dump(download_map, f, indent=2)

    print("Download complete.")

if __name__ == "__main__":
    main()
