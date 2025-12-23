import json
import os
import re
import shutil
from pypdf import PdfReader

# Constants
TEMP_DIR = "temp"
DOCS_DIR = "docs"
DOWNLOAD_MAP_FILE = os.path.join(TEMP_DIR, "download_map.json")
METADATA_FILE = os.path.join("scripts", "metadata.json")

def sanitize_filename(name):
    """Sanitizes a string to be safe for filenames."""
    # Remove characters that might be problematic
    name = re.sub(r'[^\w\s\.-]', '', name)
    # Replace spaces with dots for the specific format requested
    name = re.sub(r'\s+', '.', name)
    return name

def extract_metadata_from_pdf(filepath):
    """
    Extracts metadata from the first page of a PDF.
    Returns a dict with potential doc_number, revision, etc.
    """
    text = ""
    try:
        reader = PdfReader(filepath)
        if len(reader.pages) > 0:
            text = reader.pages[0].extract_text()
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return {}

    metadata = {}

    # Heuristics for Qualcomm docs
    # Document Number: usually 80-XXXXX-XX or LM80-XXXXX-XX
    # Example: LM80-P0436-13

    doc_num_match = re.search(r'\b([A-Z0-9]{2,4}-[A-Z0-9]{4,6}-\d+)\b', text)
    if not doc_num_match:
        # Try looser pattern
        doc_num_match = re.search(r'\b(80-[A-Z0-9]+-\d+)\b', text)

    if doc_num_match:
        metadata["doc_number"] = doc_num_match.group(1)

    # Revision: Rev. C, Rev C, Revision C, etc.
    # Often appears near the document number or date
    rev_match = re.search(r'\bRev(?:ision|\.)?\s*([A-Za-z0-9]+)\b', text, re.IGNORECASE)
    if rev_match:
        metadata["revision"] = "Rev" + rev_match.group(1).upper()
    else:
        # sometimes it's just a letter floating around, hard to catch reliably without false positives
        # let's look for known patterns like "Revision <X>"
        pass

    return metadata

def clean_title(text):
    """Cleans up the link text to be a suitable title."""
    # Remove common prefixes/suffixes
    text = text.replace("Download", "").strip()
    text = re.sub(r'\s*\(PDF\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*\(ZIP\)', '', text, flags=re.IGNORECASE)
    return text.strip()

def main():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

    if not os.path.exists(DOWNLOAD_MAP_FILE):
        print("No download map found.")
        return

    with open(DOWNLOAD_MAP_FILE, "r") as f:
        download_map = json.load(f)

    final_metadata = []

    for filename, info in download_map.items():
        filepath = os.path.join(TEMP_DIR, filename)
        if not os.path.exists(filepath):
            print(f"File missing: {filepath}")
            continue

        original_url = info["original_url"]
        link_text = info["link_text"]

        # Default values
        vendor = "Qualcomm"
        model = "APQ8016" # Default, might be DragonBoard410c for some

        # Determine model from text/link
        if "DragonBoard" in link_text or "db410c" in original_url:
            model = "DragonBoard410c"

        # Determine title
        title = clean_title(link_text)

        # Extract PDF metadata if possible
        pdf_meta = {}
        if filename.endswith(".pdf"):
            pdf_meta = extract_metadata_from_pdf(filepath)

        doc_number = pdf_meta.get("doc_number", "UNKNOWN")
        revision = pdf_meta.get("revision", "RevA") # Default to RevA if not found? Or omit?

        # Fallbacks for doc number if not found in PDF
        if doc_number == "UNKNOWN":
            # Sometimes parsing fails or it's an image-based first page.
            # We might leave it as UNKNOWN or try to identify from URL filename
            pass

        # Construct new filename
        # Pattern: Qualcomm.APQ8016.Hardware.Register.Description.LM80-P0436-13.RevC.pdf

        sanitized_title = sanitize_filename(title)

        # Handling ZIPs or files without Doc Numbers
        if doc_number == "UNKNOWN":
             new_filename = f"{vendor}.{model}.{sanitized_title}.{revision}{os.path.splitext(filename)[1]}"
        else:
             new_filename = f"{vendor}.{model}.{sanitized_title}.{doc_number}.{revision}{os.path.splitext(filename)[1]}"

        # Correct double dots if any
        new_filename = re.sub(r'\.{2,}', '.', new_filename)

        dest_path = os.path.join(DOCS_DIR, new_filename)

        # Copy file to docs/
        shutil.copy2(filepath, dest_path)
        print(f"Processed {filename} -> {new_filename}")

        final_metadata.append({
            "original_filename": filename,
            "new_filename": new_filename,
            "original_url": original_url,
            "title": title,
            "doc_number": doc_number,
            "revision": revision,
            "pdf_extraction_results": pdf_meta
        })

    # Save complete metadata
    with open(METADATA_FILE, "w") as f:
        json.dump(final_metadata, f, indent=2)

    print("Processing complete.")

if __name__ == "__main__":
    main()
