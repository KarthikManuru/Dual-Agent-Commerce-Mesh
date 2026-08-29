import json
import time
import re
from typing import Any, Callable, TypeVar, Type
import httpx
from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMExecutionError(Exception):
    """Raised when LLM_REQUIRED is True and LLM API call fails or key is missing."""
    pass


class LLMResult(BaseModel):
    data: dict[str, Any]
    reasoning_source: str  # "LLM" | "HEURISTIC_FALLBACK"
    model_name: str
    latency_ms: int
    raw_response: str | None = None


class LLMService:
    """
    LLM Client supporting Google Gemini and OpenAI with structured JSON outputs.
    Strictly surfaces reasoning_source and respects LLM_REQUIRED flag.
    """

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "You are an autonomous AI commerce agent. Respond strictly in valid JSON.",
        fallback_fn: Callable[[], dict[str, Any]] | None = None,
        model: str | None = None,
    ) -> LLMResult:
        settings = get_settings()
        start_time = time.time()

        # Check which provider to use
        gemini_key = settings.GEMINI_API_KEY
        openai_key = settings.OPENAI_API_KEY
        is_strict = settings.LLM_REQUIRED

        # 1. Try Gemini if key available
        if gemini_key:
            candidate_models = [model] if model else ["gemini-3.6-flash", "gemini-flash-latest"]
            for m in candidate_models:
                if not m:
                    continue
                try:
                    raw_text = await self._call_gemini(gemini_key, m, system_prompt, prompt)
                    parsed_json = self._extract_json(raw_text)
                    latency = int((time.time() - start_time) * 1000)
                    return LLMResult(
                        data=parsed_json,
                        reasoning_source="LLM",
                        model_name=f"gemini:{m}",
                        latency_ms=latency,
                        raw_response=raw_text,
                    )
                except Exception as e:
                    print(f"[LLMService] Gemini model {m} notice: {e}")
                    # If quota/rate-limit error (429), break immediately to fallback/OpenAI instead of slow looping
                    if "429" in str(e) or "quota" in str(e).lower():
                        break
                    continue

        # 2. Try OpenAI if key available
        if openai_key:
            model_name = model or "gpt-4o-mini"
            try:
                raw_text = await self._call_openai(openai_key, model_name, system_prompt, prompt)
                parsed_json = self._extract_json(raw_text)
                latency = int((time.time() - start_time) * 1000)
                return LLMResult(
                    data=parsed_json,
                    reasoning_source="LLM",
                    model_name=f"openai:{model_name}",
                    latency_ms=latency,
                    raw_response=raw_text,
                )
            except Exception as e:
                print(f"[LLMService] OpenAI notice: {e}")

        # 3. If strict mode enabled and no valid LLM succeeded
        if is_strict:
            raise LLMExecutionError(
                "LLM_REQUIRED=true is set, but no valid GEMINI_API_KEY or OPENAI_API_KEY was provided or the API call failed."
            )

        # 4. Fallback if permitted (fast sub-millisecond return)
        if fallback_fn:
            fallback_data = fallback_fn()
            latency = int((time.time() - start_time) * 1000)
            return LLMResult(
                data=fallback_data,
                reasoning_source="HEURISTIC_FALLBACK",
                model_name="heuristic_v1",
                latency_ms=latency,
                raw_response=None,
            )

        raise LLMExecutionError("No LLM key configured and no fallback function provided.")

    async def _call_gemini(self, api_key: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
        """Call Google Gemini generateContent REST API directly with fast 8s timeout."""
        clean_model = model_name.replace("models/", "") if model_name.startswith("models/") else model_name
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            }
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Gemini API returned HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned from Gemini: {data}")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError(f"No text parts returned: {candidates}")
            return parts[0].get("text", "{}")

    async def _call_openai(self, api_key: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
        """Call OpenAI Chat Completions REST API directly with fast 8s timeout."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"OpenAI API returned HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract and parse JSON from markdown code fences or raw text."""
        cleaned = text.strip()
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
        return json.loads(cleaned)


llm_service = LLMService()
