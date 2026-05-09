import orjson
from pathlib import Path

SEARCH_TERMS = [
    "flow",
    "debiet",
    "l/min",
    "lmin",
    "l_s",
    "ls",
    "m3h",
    "water",
    "circulation",
    "rpm",
    "pump",
]

BASE_DIR = Path("eplucon/eplucon_web/DTO/nodes")


def match_key(key: str) -> bool:
    key_lower = key.lower().replace("_", "")
    return any(term in key_lower for term in SEARCH_TERMS)


def scan_json_for_matches(data, path=""):
    """Recursively walk JSON dicts and lists and collect matching key paths."""
    matches = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if match_key(key):
                matches.append((current_path, value))

            matches.extend(scan_json_for_matches(value, current_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            matches.extend(scan_json_for_matches(item, current_path))

    return matches


def main():
    print("Scanning AJAX nodes for flow-related fields...")
    all_matches = []
    for json_file in sorted(BASE_DIR.glob("node_*.json")):
        # print(f"Processing file: {json_file}")
        try:
            with json_file.open("rb") as f:
                data = orjson.loads(f.read())
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue

        matches = scan_json_for_matches(data)
        if matches:
            print(f"\n=== Matches in {json_file.name} ===")
            for path, value in matches:
                print(f"{path}: {value}")

        all_matches.extend([(json_file.name, m[0], m[1]) for m in matches])

    # Summary
    print("\n\n===== SUMMARY =====")
    if not all_matches:
        print("No flow-related fields found at all.")
    else:
        for filename, path, value in all_matches:
            print(f"{filename}: {path} → {value}")


if __name__ == "__main__":
    main()
