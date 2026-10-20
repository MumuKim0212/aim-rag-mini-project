"""Recording of LLM and embedding calls. Every call made by rag, agent, judge, or index building goes
through record_call, so cost and call counts are comparable across teammates and experiments.

    steps = {"calls": []}
    t = time.perf_counter()
    msg = chat_model.invoke(messages)
    record_call(steps, node="generate", model=cfg["answer"]["model"], seconds=time.perf_counter() - t,
                **usage_from_message(msg))

Model client construction is left to the rag / agent / judge implementations; read model IDs and
settings from the config, never hard-code them.
"""


def record_call(steps: dict, *, node: str, model: str, kind: str = "llm", input_tokens: int = 0,
                output_tokens: int = 0, thinking_tokens: int = 0, seconds: float = 0.0, **extra) -> dict:
    """Append one call to steps["calls"]. `output_tokens` must include thinking tokens (billed as output)."""
    call = {"node": node, "kind": kind, "model": model, "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0), "thinking_tokens": int(thinking_tokens or 0),
            "seconds": round(float(seconds), 3), **extra}
    steps.setdefault("calls", []).append(call)
    return call


def usage_from_message(message) -> dict:
    """Token counts from a LangChain AIMessage's usage_metadata.

    Verified 2026-10-20 (langchain-google-genai 4.4.0, Gemini 3.x): output_tokens already includes
    thinking tokens, output_token_details.reasoning is the breakdown, and input + output == total_tokens.

    The answer text is `message.text`, not `message.content`: Gemini 3 returns content as a list of
    blocks with thought signatures.
    """
    usage = getattr(message, "usage_metadata", None) or {}
    details = usage.get("output_token_details") or {}
    return {"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
            "thinking_tokens": details.get("reasoning", 0)}
