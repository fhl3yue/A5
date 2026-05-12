from pathlib import Path
import sys
import time
import webbrowser


DEFAULT_APP_URL = "https://your-domain.example/app/"


def runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def read_app_url() -> str:
    url_file = runtime_dir() / "app-url.txt"
    if not url_file.exists():
        return DEFAULT_APP_URL

    for line in url_file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            return value
    return DEFAULT_APP_URL


def main() -> int:
    app_url = read_app_url()
    if not app_url.startswith(("http://", "https://")):
        print("Invalid app-url.txt. Use an http:// or https:// URL.")
        time.sleep(4)
        return 1

    print(f"Opening Scenic AI Guide: {app_url}")
    webbrowser.open(app_url)
    time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
