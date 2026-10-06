"""Live check: one real AI call through the router. Run: python -m app.ai.smoke"""
from pydantic import BaseModel

from app.ai.base import AIError
from app.ai.router import ai_router


class Ping(BaseModel):
    answer: str


def main() -> None:
    print("Providers:", ai_router.status())
    try:
        result = ai_router.generate("Set answer to the word pong.", Ping, tier="fast")
    except AIError as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
    print(f"OK via {result.provider} ({result.model}): {result.data.answer}")


if __name__ == "__main__":
    main()
