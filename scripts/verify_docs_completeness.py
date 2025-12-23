import json
import os
import urllib.parse

def normalize_url(url):
    """Normalize URL for comparison (handling query params if needed)."""
    # For this task, strict equality including params seems to be the expectation,
    # as the previous agent stored them with params.
    # However, order of params might vary? Probably not.
    # Let's try strict first, if it fails we can relax.
    return url.strip()

def main():
    workspace = "/Users/costan/workspace/qualcomm-apq8016e-docs"
    metadata_path = os.path.join(workspace, "scripts/metadata.json")
    docs_dir = os.path.join(workspace, "docs")
    scraped_links_path = os.path.join(workspace, "temp/scraped_links.json")

    # Load metadata
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print(f"Error: {metadata_path} not found.")
        return

    # Load scraped links
    try:
        with open(scraped_links_path, 'r') as f:
            scraped_links = json.load(f)
    except FileNotFoundError:
        print(f"Error: {scraped_links_path} not found.")
        return

    # Create map of original_url -> metadata entry
    url_to_meta = {m['original_url']: m for m in metadata}

    # Check coverage
    missing_in_metadata = []

    print(f"Checking {len(scraped_links)} scraped links against metadata...")

    for link in scraped_links:
        href = link['href']
        if href not in url_to_meta:
            # Try matching without query params just in case
            found = False
            base_href = href.split('?')[0]
            for m_url in url_to_meta:
                 if m_url.split('?')[0] == base_href:
                     found = True
                     break
            if not found:
                missing_in_metadata.append(link)

    if missing_in_metadata:
        print(f"FAIL: {len(missing_in_metadata)} links from Web Archive matching PDF/ZIP not found in metadata:")
        for l in missing_in_metadata:
            print(f"  - {l['text']}: {l['href']}")
    else:
        print("PASS: All scraped links are present in metadata.")

    # Check files in docs/
    print(f"\nChecking if files exist in {docs_dir}...")
    missing_files = []

    # Get actual files in docs
    try:
        actual_files = set(os.listdir(docs_dir))
    except FileNotFoundError:
        print(f"Error: {docs_dir} not found.")
        return

    for final_filename in actual_files:
        # Ignore .DS_Store or hidden files
        if final_filename.startswith('.'):
            continue

    # Check if every metadata entry has a corresponding file in actual_files
    # The metadata has 'new_filename' which should match a file in docs/

    meta_files_missing = []
    for m in metadata:
        fname = m['new_filename']
        if fname not in actual_files:
            meta_files_missing.append(fname)

    if meta_files_missing:
        print(f"FAIL: {len(meta_files_missing)} files listed in metadata are missing from docs/:")
        for f in meta_files_missing:
            print(f"  - {f}")
    else:
        print("PASS: All metadata entries have corresponding files in docs/.")

    # Check for files in docs/ that are NOT in metadata (orphans)
    meta_filenames = set(m['new_filename'] for m in metadata)
    orphans = []
    for f in actual_files:
        if f.startswith('.'): continue
        if f not in meta_filenames:
            orphans.append(f)

    if orphans:
        print(f"WARN: {len(orphans)} files in docs/ are not in metadata:")
        for f in orphans:
            print(f"  - {f}")
    else:
        print("PASS: No orphan files in docs/.")

if __name__ == "__main__":
    main()
