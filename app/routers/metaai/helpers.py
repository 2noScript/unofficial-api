import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "metaai-api", "src"))

from fastapi import Request
from metaai_api import MetaAI


_executor = ThreadPoolExecutor(max_workers=4)

META_MODELS = [
    {
        "id": "llama-4",
        "object": "model",
        "created": 1704067200,
        "owned_by": "meta",
        "description": "Llama 4 via Meta AI — chat with internet access, image & video generation",
    },
]


def get_client(request: Request) -> MetaAI | None:
    return getattr(request.app.state, "metaai_client", None)
