from __future__ import annotations

import json
from typing import Any

import requests


class ModelClientError(RuntimeError):
    pass


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


class DeepSeekJSONClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": json.dumps(user_payload, ensure_ascii=False),
                        },
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
                timeout=120,
            )
        except requests.RequestException as exc:
            raise ModelClientError(f"DeepSeek request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ModelClientError(f"DeepSeek request failed: {response.status_code} {response.text}")
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return extract_json_object(content)


class ZhipuChatClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def complete_json_with_image(
        self,
        prompt: str,
        image_data_url: str,
        extra_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            response = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                    + "\n\n"
                                    + json.dumps(extra_payload, ensure_ascii=False),
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_data_url},
                                },
                            ],
                        }
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
                timeout=120,
            )
        except requests.RequestException as exc:
            raise ModelClientError(f"Zhipu VLM request failed: {exc}") from exc
        if response.status_code >= 400:
            raise ModelClientError(f"Zhipu VLM request failed: {response.status_code} {response.text}")
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        return extract_json_object(content)
