#!/bin/bash

# Navigate to the script's directory
pushd "$(dirname "$0")" > /dev/null

# Directory for assets
ASSETS_DIR="assets"
mkdir -p "$ASSETS_DIR"

# List of assets to download
declare -A ASSETS
ASSETS=(
    ["tailwindcss.js"]="https://cdn.tailwindcss.com"
    ["flatpickr.min.css"]="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css"
    ["flatpickr.min.js"]="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.js"
    ["sql-wasm.js"]="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js"
    ["sql-wasm.wasm"]="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.wasm"
)

echo "Checking assets..."
for FILE in "${!ASSETS[@]}"; do
    if [ ! -f "$ASSETS_DIR/$FILE" ]; then
        echo "Downloading $FILE..."
        curl -L -o "$ASSETS_DIR/$FILE" "${ASSETS[$FILE]}"
    else
        echo "$FILE already exists."
    fi
done

echo "Starting local server on http://localhost:8000"
echo "Press Ctrl+C to stop."
python3 -m http.server 8000

# Return to original directory
popd > /dev/null
