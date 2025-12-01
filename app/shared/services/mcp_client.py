import asyncio
import shlex
from typing import Any, List, Optional

from mcp.client.session import ClientSession
from mcp.types import Tool


class MCPClient:
    """MCP 서버와 통신하는 경량 클라이언트."""

    def __init__(self, server_cmd: str, workdir: Optional[str] = None):
        self.server_cmd = server_cmd
        self.workdir = workdir
        self._session: Optional[ClientSession] = None
        self._tools_cache: Optional[List[Tool]] = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self):
        """세션이 없으면 초기화"""
        if self._session:
            return

        args = shlex.split(self.server_cmd)
        session = ClientSession()
        await session.initialize(stdio_cmd=args, cwd=self.workdir or None)
        self._session = session

    async def list_tools(self) -> List[Tool]:
        """도구 목록 조회 (캐시)"""
        async with self._lock:
            await self._ensure_session()
            if self._tools_cache is None:
                self._tools_cache = await self._session.list_tools()
            return self._tools_cache

    async def call_tool(self, name: str, arguments: Any):
        """MCP 도구 호출"""
        async with self._lock:
            await self._ensure_session()
            return await self._session.call_tool(name, arguments)