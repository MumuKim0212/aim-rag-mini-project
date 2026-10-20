"""Gemini calls and their recording. Every LLM and embedding call made by rag, agent, judge, or index
building goes through this module, so cost and call counts are comparable across teammates and experiments.

    steps = {"calls": []}
    out = generate_json(model=..., system=..., user=..., schema=AnswerOut, temperature=0,
                        thinking_level="low", steps=steps, node="generate")

Verified 2026-10-20 (google-genai 2.23.0, Gemini 3.x; scratch/check_*.py):
- usage: total = prompt + candidates + thoughts; thoughts are billed as output, so output_tokens below
  = candidates + thoughts. LangChain's usage_metadata already reports it that way (usage_from_message).
- LangChain answer text is `message.text`, not `message.content` (Gemini 3 returns content blocks).
- embed_content reports no token usage: index building counts tokens with count_tokens; query embeddings
  are estimated from the index's tokens-per-character ratio and recorded with estimated=True.
- response_schema (pydantic) works with thinking_level; response.parsed holds the object.
- describe_image: page image + text for extraction (src/rag/ingest.py supplement_visuals).
- gemini-embedding-2 (multimodal) merges a list[str] into ONE vector; a list of Content objects gives one
  vector per text, identical to single calls (cosine 1.0). gemini-embedding-001 handles both forms.
"""

import threading
import time

from google import genai
from google.genai import errors, types

from .env import require_api_key

RETRY_CODES = {429, 500, 502, 503, 504}
_clients: dict = {}
_lock = threading.Lock()


def client(timeout_s: float | None = None) -> genai.Client:
    with _lock:
        if timeout_s not in _clients:
            options = types.HttpOptions(timeout=int(timeout_s * 1000)) if timeout_s else None
            _clients[timeout_s] = genai.Client(api_key=require_api_key(), http_options=options)
        return _clients[timeout_s]


def with_retry(fn, retries: int = 2, base_delay: float = 2.0):
    for attempt in range(retries + 1):
        try:
            return fn()
        except errors.APIError as e:
            if e.code not in RETRY_CODES or attempt == retries:
                raise
            time.sleep(base_delay * 2 ** attempt)


def record_call(steps: dict, *, node: str, model: str, kind: str = "llm", input_tokens: int = 0,
                output_tokens: int = 0, thinking_tokens: int = 0, seconds: float = 0.0, **extra) -> dict:
    """Append one call to steps["calls"]. `output_tokens` must include thinking tokens (billed as output)."""
    call = {"node": node, "kind": kind, "model": model, "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0), "thinking_tokens": int(thinking_tokens or 0),
            "seconds": round(float(seconds), 3), **extra}
    steps.setdefault("calls", []).append(call)
    return call


def usage_from_genai(response) -> dict:
    u = response.usage_metadata
    thoughts = (u.thoughts_token_count or 0) if u else 0
    return {"input_tokens": (u.prompt_token_count or 0) if u else 0,
            "output_tokens": ((u.candidates_token_count or 0) if u else 0) + thoughts,
            "thinking_tokens": thoughts}


def usage_from_message(message) -> dict:
    """Token counts from a LangChain AIMessage (for code that calls Gemini through LangChain)."""
    usage = getattr(message, "usage_metadata", None) or {}
    details = usage.get("output_token_details") or {}
    return {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
            "thinking_tokens": details.get("reasoning", 0)}


def generate_json(*, model: str, system: str, user: str, schema, temperature: float | None,
                  thinking_level: str | None, steps: dict, node: str, retries: int = 2,
                  timeout_s: float | None = None):
    """One structured-output call; returns an instance of `schema` (pydantic). Raises if unparseable."""
    config = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature, response_mime_type="application/json",
        response_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if thinking_level else None)
    start = time.perf_counter()
    response = with_retry(lambda: client(timeout_s).models.generate_content(model=model, contents=user, config=config),
                          retries)
    record_call(steps, node=node, model=model, seconds=time.perf_counter() - start, **usage_from_genai(response))
    if response.parsed is None:
        raise ValueError(f"{node}: response did not match the schema: {(response.text or '')[:200]!r}")
    return response.parsed


def _task_type(embedding_cfg: dict, purpose: str) -> str | None:
    if embedding_cfg.get("task_type") == "retrieval":  # gemini-embedding-001 only
        return "RETRIEVAL_QUERY" if purpose == "query" else "RETRIEVAL_DOCUMENT"
    return embedding_cfg.get("task_type")


def _contents(texts: list[str]) -> list:
    return [types.Content(parts=[types.Part(text=t)]) for t in texts]


def count_tokens(texts: list[str], model: str, retries: int = 2) -> int:
    return with_retry(lambda: client().models.count_tokens(model=model, contents=_contents(texts)),
                      retries).total_tokens


def embed(texts: list[str], *, embedding_cfg: dict, purpose: str, steps: dict, node: str,
          tokens: int, estimated: bool = False, retries: int = 2) -> list[list[float]]:
    """Embed texts (purpose: "document" | "query") and record the call with the given token count."""
    config = types.EmbedContentConfig(output_dimensionality=embedding_cfg["dimensions"],
                                      task_type=_task_type(embedding_cfg, purpose))
    start = time.perf_counter()
    response = with_retry(lambda: client().models.embed_content(model=embedding_cfg["model"],
                                                                contents=_contents(texts), config=config), retries)
    record_call(steps, node=node, model=embedding_cfg["model"], kind="embedding", input_tokens=tokens,
                seconds=time.perf_counter() - start, estimated=estimated, n_texts=len(texts))
    vectors = [e.values for e in response.embeddings]
    if len(vectors) != len(texts):
        raise ValueError(f"{embedding_cfg['model']}: {len(vectors)} vectors for {len(texts)} texts")
    return vectors


def describe_image(*, model: str, system: str, user: str, png: bytes, thinking_level: str | None, steps: dict,
                   node: str, retries: int = 2, timeout_s: float | None = None) -> tuple[str, str | None]:
    """One image + text call (page extraction). Returns (text, finish_reason); text is "" when blocked
    (e.g. finish_reason RECITATION: Gemini refuses verbatim copies of published text)."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level) if thinking_level else None)
    contents = [types.Content(role="user", parts=[types.Part.from_bytes(data=png, mime_type="image/png"),
                                                  types.Part(text=user)])]
    start = time.perf_counter()
    response = with_retry(lambda: client(timeout_s).models.generate_content(model=model, contents=contents,
                                                                            config=config), retries)
    finish = response.candidates[0].finish_reason if response.candidates else None
    finish = getattr(finish, "name", finish)
    record_call(steps, node=node, model=model, seconds=time.perf_counter() - start, finish_reason=finish,
                **usage_from_genai(response))
    try:
        text = response.text or ""
    except ValueError:  # no text part (blocked)
        text = ""
    return text.strip(), finish
