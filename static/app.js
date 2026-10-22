"use strict";
const $ = id => document.getElementById(id);
for (const button of document.querySelectorAll("[data-q]")) button.onclick = () => { $("question").value = button.dataset.q; $("question").focus(); };
fetch("/api/health").then(r => r.json()).then(body => $("status").textContent = `知识库已连接 · ${body.chunks} 个片段`).catch(() => $("status").textContent = "连接失败，请先启动 Python 服务");
$("form").onsubmit = async event => {
  event.preventDefault(); $("submit").disabled = true; $("status").textContent = "正在检索…";
  try {
    const response = await fetch("/api/ask", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question:$("question").value, top_k:3})});
    if (!response.ok) throw new Error("输入有误或服务不可用，请检查问题长度");
    const result = await response.json(); $("empty").hidden = true; $("sources").replaceChildren();
    $("result-title").textContent = result.abstained ? "暂未找到依据" : `找到 ${result.sources.length} 份相关摘录`;
    if (result.abstained) { const p = document.createElement("p"); p.textContent = result.answer; $("sources").append(p); }
    for (const source of result.sources) {
      const card = document.createElement("article"), heading = document.createElement("h3"), meta = document.createElement("div"), text = document.createElement("p");
      heading.textContent = source.heading || source.source; meta.className = "meta"; meta.textContent = `${source.source} · L${source.start_line}-${source.end_line} · ${source.id}`; text.textContent = source.text;
      card.append(heading, meta, text); $("sources").append(card);
    }
    $("notice").textContent = result.notice; $("status").textContent = `检索完成 · ${result.latency_ms} ms（单次本地耗时）`;
  } catch (error) { $("status").textContent = error.message; }
  finally { $("submit").disabled = false; }
};
