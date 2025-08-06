import httpx


class APIGatewayClient(httpx.AsyncClient):
    async def request_json(self, method: str, url: str, **kw):
        r = await self.request(method, url, **kw)
        r.raise_for_status()
        return r.json()

    async def get_profile(self, tg_user_id: int):
        return await self.request_json("GET", f"/verify{tg_user_id}")

    async def register_user(self, tg_user_id: str, name: str, dob_iso: str):
        body = {"name": name, "tgid": tg_user_id, "birthdate": dob_iso}
        print(body)
        return await self.request_json("POST", "/register", json=body)
