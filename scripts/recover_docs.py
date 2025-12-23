import requests
import os
import json

TEMP_DIR = "temp"
RECOVERY_TARGETS = [
    {
        "filename": "doc_037.pdf",
        "url": "https://developer.qualcomm.com/qfile/28821/lm80-p0436-1_little_kernel_boot_loader_overview.pdf"
    },
    {
        "filename": "doc_048.pdf",
        "url": "https://developer.qualcomm.com/qfile/28819/lm80-p0436-5_peripherals_programming_guide.pdf"
    }
]

def get_best_snapshot(url):
    cdx_api = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,statuscode,mimetype,original",
        "collapse": "timestamp:6" # one per month roughly
    }
    try:
        resp = requests.get(cdx_api, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None

        # data[0] is header
        snapshots = data[1:]
        # Filter for 200 and pdf
        valid = [s for s in snapshots if s[1] == "200" and "pdf" in s[2].lower()]

        if valid:
            # Pick the most recent one ? Or one from 2023?
            # 2023 snapshot was 403. Let's pick the LAST valid one.
            # snapshots are usually sorted by timestamp? Yes.
            best = valid[-1]
            print(f"  Found snapshot: {best[0]} ({best[1]})")
            return f"https://web.archive.org/web/{best[0]}id_/{best[3]}"

    except Exception as e:
        print(f"Error querying CDX for {url}: {e}")
    return None

def download_file(url, filepath):
    print(f"Downloading {url} to {filepath}...")
    try:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print("  Success!")
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def main():
    for target in RECOVERY_TARGETS:
        print(f"Recovering {target['filename']}...")
        wb_url = get_best_snapshot(target["url"])
        if wb_url:
            path = os.path.join(TEMP_DIR, target["filename"])
            download_file(wb_url, path)
        else:
            print(f"  No valid snapshot found for {target['url']}")

if __name__ == "__main__":
    main()
