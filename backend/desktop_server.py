from __future__ import annotations

import argparse
import os

import uvicorn

from backend.main import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("COURTTRACE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("COURTTRACE_PORT", "8000")))
    options = parser.parse_args()
    uvicorn.run(app, host=options.host, port=options.port)
