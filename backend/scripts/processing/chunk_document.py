import argparse
import json
import os
import re
from typing import Optional, Tuple, List, Dict


DELIMITER_WITH_LABEL = re.compile(r"(?P<label>\S+)\s+--PAGE\s+(?P<number>\d+)\s+END--")
DELIMITER_NO_LABEL = re.compile(r"--PAGE\s+(?P<number>\d+)\s+END--")


def load_regex(regex_path: str) -> str:
    with open(regex_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle.read().splitlines() if line.strip()]
        pattern = lines[0] if lines else ""
    if not pattern:
        raise ValueError(f"Regex file is empty: {regex_path}")
    return pattern


def split_pages(text: str, pattern: str) -> List[str]:
    delimiter_pattern = pattern
    if pattern.startswith("(?<=") and pattern.endswith(")"):
        delimiter_pattern = pattern[4:-1]

    regex = re.compile(delimiter_pattern)
    chunks = []
    start = 0
    for match in regex.finditer(text):
        end = match.end()
        chunks.append(text[start:end])
        start = end

    if start < len(text):
        chunks.append(text[start:])

    # Remove trailing empty chunk if the text ends with the delimiter.
    if chunks and chunks[-1] == "":
        chunks.pop()
    return chunks


def extract_page_meta(chunk: str) -> Tuple[int, Optional[str]]:
    matches = list(DELIMITER_WITH_LABEL.finditer(chunk))
    if matches:
        last = matches[-1]
        return int(last.group("number")), last.group("label")

    no_label_matches = list(DELIMITER_NO_LABEL.finditer(chunk))
    if no_label_matches:
        last = no_label_matches[-1]
        return int(last.group("number")), None

    raise ValueError("No page delimiter found in chunk.")


def build_output(document_name: str, source_path: str, regex: str, chunks: List[str]) -> Dict:
    pages = []
    for index, chunk in enumerate(chunks, start=1):
        page_number, page_label = extract_page_meta(chunk)
        page = {
            "page_index": index,
            "page_number": page_number,
            "text": chunk,
        }
        if page_label is not None:
            page["page_label"] = page_label
        pages.append(page)

    return {
        "document_name": document_name,
        "source_path": source_path,
        "chunking": {
            "regex": regex,
            "strategy": "split_on_delimiter_match",
        },
        "pages": pages,
    }


def default_output_path(input_path: str) -> str:
    base, _ext = os.path.splitext(input_path)
    return f"{base}.chunked.json"


def chunk_document_file(
    input_path: str,
    regex_path: str,
    output_path: Optional[str] = None,
    document_name: Optional[str] = None,
) -> Tuple[Dict, str]:
    output_path = output_path or default_output_path(input_path)

    with open(input_path, "r", encoding="utf-8") as handle:
        source_text = handle.read()

    regex = load_regex(regex_path)
    chunks = split_pages(source_text, regex)
    if not chunks:
        raise ValueError("No chunks produced; check the regex and source format.")

    document_name = document_name or os.path.basename(input_path)
    payload = build_output(document_name, input_path, regex, chunks)

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2)

    return payload, output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunk a document into page JSON.")
    parser.add_argument("--input", required=True, help="Path to source text file.")
    parser.add_argument("--regex-file", required=True, help="Path to regex file.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <input>.chunked.json).",
    )
    parser.add_argument(
        "--document-name",
        default=None,
        help="Optional human-friendly document name.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload, output_path = chunk_document_file(
        input_path=args.input,
        regex_path=args.regex_file,
        output_path=args.output,
        document_name=args.document_name,
    )

    print(f"Wrote {len(payload['pages'])} pages to {output_path}")


if __name__ == "__main__":
    main()
