import requests
from dataclasses import dataclass
from pydantic import SecretStr

from typedef.cmd_data_types import EmbeddingApiConfig

from langchain.embeddings.base import Embeddings

EMBEDDING_HANDLER_DEBUG_FLAG = False


class EmbeddingHandler(Embeddings):
    def __init__(self, api_config: EmbeddingApiConfig):
        self.base_url = api_config.base_url
        self.api_key = api_config.api_key
        self.model = api_config.model
        self.init_embedding_handler()

    def embed_documents(self, texts: list) -> list:
        embeddings = []
        for text in texts:
            embedding = self._get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text) -> list:
        return self._get_embedding(text)

    def _get_embedding(self, text: str) -> list:
        # Ensure the text ends with a separator token if required
        payload = {
            "model": self.model,
            "input": text + " [SEP]"
        }
        response = requests.post(
            f"{self.base_url}embeddings",
            json=payload
        )
        response.raise_for_status()
        return response.json().get('data')[0].get('embedding')

    def init_embedding_handler(self):
        # 实际上是测试连接性
        payload = {
            "model": self.model,
            "input": "test string"
        }
        headers = {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{self.base_url}embeddings",
            json=payload,
            headers=headers
        )
        if EMBEDDING_HANDLER_DEBUG_FLAG:
            print(response.json())
        response.raise_for_status()
        if response.status_code == 200:
            print("Embedding API connection successful")
        else:
            print("Embedding API connection failed !!!")

