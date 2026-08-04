#!/usr/bin/env bash
set -e

if [ ! -f .env ]; then
    echo "Error: .env file not found. Copy .env.example to .env and fill in credentials."
    exit 1
fi

ensure_ds_free_api_binary() {
    if [ -f "./bin/ds-free-api" ]; then
        return 0
    fi

    echo "[DeepSeek Engine] Binary not found. Detecting OS and downloading prebuilt release..."
    mkdir -p bin

    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"

    case "$ARCH" in
        x86_64|amd64) ARCH_TAG="x86_64" ;;
        aarch64|arm64) ARCH_TAG="aarch64" ;;
        *) echo "[DeepSeek Engine] Error: Unsupported architecture $ARCH"; return 1 ;;
    esac

    VERSION="v0.2.6"
    case "$OS" in
        darwin)
            FILE="ds-free-api-${VERSION}-macos-${ARCH_TAG}.tar.gz"
            ;;
        linux)
            FILE="ds-free-api-${VERSION}-linux-${ARCH_TAG}-musl.tar.gz"
            ;;
        mingw*|cygwin*|msys*)
            FILE="ds-free-api-${VERSION}-windows-${ARCH_TAG}.zip"
            ;;
        *)
            echo "[DeepSeek Engine] Error: Unsupported OS $OS"
            return 1
            ;;
    esac

    URL="https://github.com/NIyueeE/ds-free-api/releases/download/${VERSION}/${FILE}"
    echo "[DeepSeek Engine] Downloading ${URL}..."
    curl -sSL "$URL" -o "/tmp/$FILE"

    if [[ "$FILE" == *.tar.gz ]]; then
        tar -xzf "/tmp/$FILE" -C /tmp/
        mv /tmp/ds-free-api-${VERSION}-*/ds-free-api bin/ds-free-api 2>/dev/null || mv /tmp/ds-free-api bin/ds-free-api
    elif [[ "$FILE" == *.zip ]]; then
        unzip -q "/tmp/$FILE" -d /tmp/
        mv /tmp/ds-free-api-${VERSION}-*/ds-free-api.exe bin/ds-free-api 2>/dev/null || mv /tmp/ds-free-api.exe bin/ds-free-api
    fi
    rm -f "/tmp/$FILE"
    chmod +x bin/ds-free-api
    echo "[DeepSeek Engine] Ready at ./bin/ds-free-api"
}

# Auto-start ds-free-api background engine if not running
if ! pgrep -f "ds-free-api" > /dev/null; then
    ensure_ds_free_api_binary

    if [ -f "./bin/ds-free-api" ]; then
        echo "[DeepSeek Engine] Starting background service on port 22217..."
        mkdir -p ds-free-api-data
        (cd ds-free-api-data && "../bin/ds-free-api" > /dev/null 2>&1 &)
        sleep 2
    else
        echo "[DeepSeek Engine] Warning: Binary not found at ./bin/ds-free-api"
    fi
fi

uv run uvicorn core.server:app --host 0.0.0.0 --port 8088 --reload
