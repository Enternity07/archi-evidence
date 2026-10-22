import importlib.util
import tempfile
import unittest
from pathlib import Path

AVAILABLE = importlib.util.find_spec("mcp") is not None


@unittest.skipUnless(AVAILABLE, "Install requirements-mcp.txt on Python 3.11+ for MCP tests")
class McpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from archi_agent.mcp_server import create_server
        from archi_agent.retrieval import KnowledgeBase
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "mcp.sqlite3"
        KnowledgeBase(path).index(Path(__file__).resolve().parents[1] / "sample_notes")
        self.server = create_server(path)

    def tearDown(self):
        self.temp.cleanup()

    async def test_search_protocol(self):
        from mcp import Client
        async with Client(self.server) as client:
            result = await client.call_tool("search_notes", {"query": "RAG"})
            self.assertTrue(result.structured_content["hits"])
            self.assertIn("start_line", result.structured_content["hits"][0])

    async def test_calculate_protocol(self):
        from mcp import Client
        async with Client(self.server) as client:
            result = await client.call_tool("calculate", {"expression": "(12*8)/3"})
            self.assertEqual(result.structured_content["value"], 32)

    async def test_only_allowlisted_tools_are_exposed(self):
        from mcp import Client
        async with Client(self.server) as client:
            tools = await client.list_tools()
            self.assertEqual({item.name for item in tools.tools}, {"search_notes", "calculate"})
