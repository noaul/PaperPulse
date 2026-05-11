import httpx


class WeKnoraClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30):
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_manual_knowledge(
        self,
        knowledge_base_id: str,
        title: str,
        content: str,
        channel: str = "api",
    ) -> dict:
        url = f"{self.base_url}/knowledge-bases/{knowledge_base_id}/knowledge/manual"
        payload = {
            "title": title,
            "content": content,
            "status": "publish",
            "channel": channel,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

    async def list_knowledge_bases(self) -> dict:
        url = f"{self.base_url}/knowledge-bases"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()
