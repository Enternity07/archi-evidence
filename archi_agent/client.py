"""Minimal Chat Completions transport; all credentials come from environment."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ChatClient:
    def __init__(self):
        self.key = os.environ.get("LLM_API_KEY", "")
        self.base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "")
        url = urlsplit(self.base)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("LLM_BASE_URL 必须是无凭据、无查询参数的 HTTPS 地址")
        if not self.key or not self.model:
            raise ValueError("在线模式需设置 LLM_API_KEY 和 LLM_MODEL")
        self.opener = build_opener(NoRedirect())

    def complete(self, messages, tools):
        payload = {"model": self.model, "messages": messages, "tools": tools,
                   "temperature": 0, "max_tokens": 1400}
        if urlsplit(self.base).hostname == "api.deepseek.com":
            payload["thinking"] = {"type": "disabled"}
        req = Request(self.base + "/chat/completions", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
        try:
            with self.opener.open(req, timeout=40) as response:
                raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("模型响应超过 1 MB")
            body = json.loads(raw)
            message = body["choices"][0]["message"]
            if not isinstance(message, dict) or message.get("role") != "assistant":
                raise ValueError("模型消息格式错误")
            return message, body.get("usage", {})
        except HTTPError as error:
            raise RuntimeError(f"模型接口 HTTP {error.code}；请检查模型名、密钥、额度和服务商文档") from None
        except (URLError, TimeoutError):
            raise RuntimeError("模型接口连接失败或超时") from None
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise RuntimeError("模型响应不符合 Chat Completions 格式") from None
