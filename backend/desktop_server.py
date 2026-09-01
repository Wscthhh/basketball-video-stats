from __future__ import annotations

import os

import uvicorn

from backend.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("COURTTRACE_PORT", "8000")))
