import requests
import pytest

from app.model_clients import ModelClientError, ZhipuChatClient


def test_zhipu_client_wraps_request_timeout_as_model_client_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(requests, "post", raise_timeout)
    client = ZhipuChatClient("key", "glm-4v-flash")

    with pytest.raises(ModelClientError, match="Zhipu VLM request failed"):
        client.complete_json_with_image(
            prompt="Return JSON",
            image_data_url="data:image/jpeg;base64,AAAA",
            extra_payload={},
        )
