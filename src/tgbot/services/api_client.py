import httpx


class APIGatewayClient(httpx.AsyncClient):
    async def request_json(self, method: str, url: str, **kw):
        r = await self.request(method, url, **kw)
        r.raise_for_status()
        return r.json()

    async def user_exists(self, tg_user_id: int) -> bool:
        data = await self.request_json("GET", f"/check_user?tgid={tg_user_id}")
        return bool(data.get("exists"))

    async def register_user(self, tg_user_id: int, name: str, dob_iso: str):
        body = {"name": name, "tgid": str(tg_user_id), "birthdate": dob_iso}
        print(body)
        return await self.request_json("POST", "/register", json=body)

    async def get_subjects(self) -> list[str]:
        data = await self.request_json("GET", "/listsubjects")
        return [str(s) for s in (data.get("subjects") or [])]

    async def get_subject_sections(self, tg_user_id: int, subject: str) -> list[dict]:
        body = {"tgid": str(tg_user_id), "subject": subject}
        data = await self.request_json("POST", "/subjectsections", json=body)
        return list(data.get("sections") or [])

    async def get_section_topics(self, section_title: str) -> dict:
        body = {"section_title": section_title}
        return await self.request_json("POST", "/sectiontopics", json=body)

    async def get_sections_total(self, tg_user_id: int, sections: list[str]) -> dict:
        body = {"tgid": str(tg_user_id), "sections": sections}
        return await self.request_json("POST", "/sections/total", json=body)

    async def create_payment_sections(self, tg_user_id: int, sections: list[str]) -> dict:
        body = {"tgid": str(tg_user_id), "sections": sections}
        return await self.request_json("POST", "/createpayment", json=body)