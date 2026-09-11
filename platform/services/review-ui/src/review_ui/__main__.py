from __future__ import annotations

import uvicorn

from review_ui.app import app


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8092, log_level="info")


if __name__ == "__main__":
    main()
