import json
import os

MAP_FILE = "temp/download_map.json"

def main():
    with open(MAP_FILE, "r") as f:
        data = json.load(f)

    # Add missing entries
    if "doc_037.pdf" not in data:
        data["doc_037.pdf"] = {
            "original_url": "https://developer.qualcomm.com/download/db410c/lk-overview-db410.pdf",
            "download_url": "RECOVERED",
            "link_text": "Little Kernel Boot Loader Overview"
        }

    if "doc_048.pdf" not in data:
        data["doc_048.pdf"] = {
            "original_url": "https://developer.qualcomm.com/download/db410c/peripherals-programming-guide-linux-android.pdf",
            "download_url": "RECOVERED",
            "link_text": "Peripherals Programming Guide, Linux Android"
        }

    with open(MAP_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print("Updated download_map.json")

if __name__ == "__main__":
    main()
