const sampleText = [
  "数字经济里数据要素和平台经济的区别还不够清楚，希望老师补充企业案例。",
  "Python 数据处理作业有点难，pandas 报错后不知道怎么定位问题。",
  "飞书通知很及时，课件资料也方便查找。",
  "考试范围和评分标准希望提前说明，不然复习压力比较大。",
  "论文选题想结合直播电商和平台治理，希望有文献阅读模板。",
  "课堂节奏有时太快，基础弱的同学来不及跟上。",
].join("\n");

let lastResult = null;

const $ = (id) => document.getElementById(id);

window.addEventListener("DOMContentLoaded", () => {
  loadRuntimeConfig();
  $("sampleBtn").addEventListener("click", () => {
    $("feedbackText").value = sampleText;
    setStatus("样例已载入");
  });
  $("clearBtn").addEventListener("click", () => {
    $("feedbackText").value = "";
    $("fileInput").value = "";
    setStatus("已清空");
  });
  $("analyzeBtn").addEventListener("click", analyze);
  $("markdownBtn").addEventListener("click", downloadMarkdown);
  $("csvBtn").addEventListener("click", downloadCsv);
  $("feishuBtn").addEventListener("click", pushFeishu);
});

async function loadRuntimeConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    const ai = data.ai || {};
    const label = ai.enabled ? `Live AI · ${ai.model || "model"}` : "Rules fallback";
    $("aiBadge").textContent = label;
    $("aiBadge").classList.toggle("live", Boolean(ai.enabled));
  } catch (_error) {
    $("aiBadge").textContent = "Runtime unknown";
  }
}

async function analyze() {
  setStatus("分析中");
  setBusy(true);
  try {
    const file = $("fileInput").files[0];
    let csv = "";
    let fileText = "";
    if (file) {
      fileText = await file.text();
      if (file.name.toLowerCase().endsWith(".csv")) {
        csv = fileText;
      } else {
        $("feedbackText").value = fileText;
      }
    }
    const payload = {
      text: csv ? $("feedbackText").value : $("feedbackText").value || fileText,
      csv,
    };
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!data.ok) {
      setStatus(data.error || "分析失败", true);
      return;
    }
    lastResult = data.result;
    renderResult(lastResult);
    setStatus(lastResult.warnings?.length ? lastResult.warnings[0] : "分析完成");
  } catch (error) {
    setStatus(`请求失败：${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

function renderResult(result) {
  $("generatedAt").textContent = result.generated_at || "已生成";
  $("metricTotal").textContent = result.total ?? 0;
  $("metricNegative").textContent = result.sentiment_counts?.["负向"] ?? 0;
  $("metricHigh").textContent = result.priority_counts?.["高"] ?? 0;
  $("summaryText").textContent = result.summary || "无摘要。";
  $("reportPreview").textContent = result.report_markdown || "";
  $("markdownBtn").disabled = !result.report_markdown;
  $("csvBtn").disabled = !result.items?.length;
  $("feishuBtn").disabled = !result.total;
  renderTopics(result.category_counts || {});
  renderRecommendations(result.recommendations || []);
  renderRows(result.items || []);
}

function renderTopics(counts) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    $("categoryBars").innerHTML = "";
    return;
  }
  const max = entries.reduce((value, [, count]) => Math.max(value, count), 1);
  $("categoryBars").innerHTML = entries
    .map(([category, count]) => {
      const width = Math.max(7, Math.round((count / max) * 100));
      return `
        <div class="topic-row">
          <span title="${escapeHtml(category)}">${escapeHtml(category)}</span>
          <div class="topic-track"><div class="topic-fill" style="width:${width}%"></div></div>
          <strong>${count}</strong>
        </div>`;
    })
    .join("");
}

function renderRecommendations(items) {
  const html = items.length
    ? items
        .map((item, index) => `<div class="recommendation">${index + 1}. ${escapeHtml(item)}</div>`)
        .join("")
    : `<p class="empty-line">暂无建议。</p>`;
  $("recommendations").innerHTML = html;
}

function renderRows(items) {
  if (!items.length) {
    $("detailRows").innerHTML = `<tr><td colspan="6" class="empty-cell">暂无数据</td></tr>`;
    return;
  }
  $("detailRows").innerHTML = items
    .map((row) => {
      const item = row.item || {};
      return `
        <tr>
          <td>${escapeHtml(item.id || "")}</td>
          <td>${escapeHtml(item.text || "")}</td>
          <td>${escapeHtml(row.category || "")}</td>
          <td>${pill(row.sentiment || "")}</td>
          <td>${pill(row.priority || "")}</td>
          <td>${escapeHtml(row.action || "")}</td>
        </tr>`;
    })
    .join("");
}

function pill(value) {
  const cls = value === "负向" || value === "高" ? "bad" : value === "中" ? "mid" : "good";
  return `<span class="pill ${cls}">${escapeHtml(value)}</span>`;
}

async function pushFeishu() {
  if (!lastResult) return;
  setStatus("推送中");
  try {
    const response = await fetch("/api/feishu", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        webhook: $("webhookInput").value.trim(),
        secret: $("secretInput").value.trim(),
        result: lastResult,
      }),
    });
    const data = await response.json();
    setStatus(data.message || (data.ok ? "推送成功" : "推送失败"), !data.ok);
  } catch (error) {
    setStatus(`推送失败：${error.message}`, true);
  }
}

function downloadMarkdown() {
  if (!lastResult?.report_markdown) return;
  download("feedback_report.md", lastResult.report_markdown, "text/markdown");
}

function downloadCsv() {
  if (!lastResult?.items?.length) return;
  const header = ["id", "text", "category", "sentiment", "priority", "keywords", "action"];
  const rows = lastResult.items.map((row) => [
    row.item?.id || "",
    row.item?.text || "",
    row.category || "",
    row.sentiment || "",
    row.priority || "",
    (row.keywords || []).join(";"),
    row.action || "",
  ]);
  const csv = [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  download("feedback_analysis.csv", csv, "text/csv");
}

function download(filename, content, type) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setBusy(isBusy) {
  $("analyzeBtn").disabled = isBusy;
  $("analyzeBtn").textContent = isBusy ? "分析中" : "分析反馈";
}

function setStatus(text, isError = false) {
  $("statusText").textContent = text;
  $("statusText").style.color = isError ? "var(--red)" : "var(--muted)";
}

