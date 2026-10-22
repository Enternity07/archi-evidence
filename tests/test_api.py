import importlib.util
import tempfile
import unittest
from pathlib import Path

AVAILABLE = all(importlib.util.find_spec(name) for name in ["fastapi", "httpx"])


@unittest.skipUnless(AVAILABLE, "Install requirements-dev.txt to test the optional FastAPI service")
class ApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from archi_agent.api import create_app
        from archi_agent.retrieval import KnowledgeBase
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "api.sqlite3"
        KnowledgeBase(path).index(Path(__file__).resolve().parents[1] / "sample_notes")
        self.client = TestClient(create_app(path))

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_ask_with_sources(self):
        response = self.client.post("/api/ask", json={"question": "RAG 是什么？"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["sources"])
        self.assertEqual(response.json()["mode"], "offline-extractive")

    def test_input_validation(self):
        for payload in [{"question": ""}, {"question": "   "}, {"question": "x" * 2001}, {"question": "RAG", "top_k": 99}, {"question": "RAG", "top_k": True}]:
            self.assertEqual(self.client.post("/api/ask", json=payload).status_code, 422)

    def test_health_and_static(self):
        self.assertGreater(self.client.get("/api/health").json()["chunks"], 0)
        for path in ["/", "/app.js", "/style.css"]:
            self.assertEqual(self.client.get(path).status_code, 200)
