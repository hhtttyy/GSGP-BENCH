#!/usr/bin/env node
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_OUT = path.join(ROOT, "site/data/prospective/submissions.json");
const CONFIDENCE = new Set(["low", "low_medium", "medium", "medium_high", "high"]);
const ALGORITHMS = ["gblup", "ifam", "sbayesrc", "bayesr", "bayesb", "bayesc"];
const DATASETS = ["sim1000g", "sim500", "duroc", "rice", "ukb", "wtccc"];

function parsePrUrl(value) {
  const url = new URL(value);
  if (url.hostname !== "github.com") throw new Error("Only github.com PR URLs are supported.");
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length < 4 || parts[2] !== "pull") throw new Error("Expected a URL like https://github.com/owner/repo/pull/123.");
  return { owner: parts[0], repo: parts[1], number: Number(parts[3]) };
}

function githubHeaders() {
  const headers = {
    accept: "application/vnd.github+json",
    "user-agent": "gsgp-bench-prospective-bot"
  };
  if (process.env.GITHUB_TOKEN) headers.authorization = `Bearer ${process.env.GITHUB_TOKEN}`;
  return headers;
}

async function fetchPrInput(prUrl) {
  const { owner, repo, number } = parsePrUrl(prUrl);
  const api = `https://api.github.com/repos/${owner}/${repo}/pulls/${number}`;
  const prResponse = await fetch(api, { headers: githubHeaders() });
  if (!prResponse.ok) throw new Error(`GitHub PR fetch failed: ${prResponse.status}`);
  const pr = await prResponse.json();
  const diffResponse = await fetch(api, {
    headers: { ...githubHeaders(), accept: "application/vnd.github.v3.diff" }
  });
  if (!diffResponse.ok) throw new Error(`GitHub diff fetch failed: ${diffResponse.status}`);
  const diff = await diffResponse.text();
  return {
    url: pr.html_url,
    title: pr.title || "",
    body: pr.body || "",
    head_sha: pr.head?.sha || "",
    author: pr.user?.login || null,
    diff: diff.slice(0, 120_000)
  };
}

function extractJson(text) {
  const raw = String(text || "").trim();
  try { return JSON.parse(raw); } catch {}
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start >= 0 && end > start) return JSON.parse(raw.slice(start, end + 1));
  throw new Error("Model did not return a JSON object.");
}

function assertStringArray(value, label) {
  if (!Array.isArray(value) || value.length < 1 || value.some((item) => typeof item !== "string" || item.trim().length < 3)) {
    throw new Error(`${label} must be a non-empty string array.`);
  }
}

export function validateProspectivePayload(payload, sourcePr) {
  if (!payload || typeof payload !== "object") throw new Error("Payload must be an object.");
  if (!Array.isArray(payload.records) || payload.records.length < 1) throw new Error("records must be non-empty.");
  const records = payload.records.map((record) => {
    if (!ALGORITHMS.includes(record.algorithm_id)) throw new Error(`Unknown algorithm_id: ${record.algorithm_id}`);
    if (!DATASETS.includes(record.dataset_id)) throw new Error(`Unknown dataset_id: ${record.dataset_id}`);
    if (!Number.isInteger(record.expected) || record.expected < 0 || record.expected > 100) {
      throw new Error("expected must be an integer from 0 to 100.");
    }
    if (!CONFIDENCE.has(record.confidence)) throw new Error(`Invalid confidence: ${record.confidence}`);
    if (record.tool_status !== "unverified") throw new Error("tool_status must be unverified before human validation.");
    if (record.validation_status !== "pending_validation") throw new Error("validation_status must be pending_validation.");
    const reasoning = record.reasoning || {};
    if (typeof reasoning.summary !== "string" || reasoning.summary.trim().length < 10) throw new Error("reasoning.summary is required.");
    assertStringArray(reasoning.evidence, "reasoning.evidence");
    assertStringArray(reasoning.risks, "reasoning.risks");
    assertStringArray(reasoning.verification_plan, "reasoning.verification_plan");
    return {
      algorithm_id: record.algorithm_id,
      dataset_id: record.dataset_id,
      expected: record.expected,
      confidence: record.confidence,
      estimate_label: String(record.estimate_label || "待验证"),
      expected_metrics: {
        pearson: record.expected_metrics?.pearson || null,
        r2: record.expected_metrics?.r2 || null,
        auc: record.expected_metrics?.auc || null,
        runtime: record.expected_metrics?.runtime || null
      },
      tool_status: "unverified",
      validation_status: "pending_validation",
      source_submission: record.source_submission || null,
      reasoning: {
        summary: reasoning.summary.trim(),
        evidence: reasoning.evidence.map((x) => x.trim()),
        risks: reasoning.risks.map((x) => x.trim()),
        verification_plan: reasoning.verification_plan.map((x) => x.trim())
      }
    };
  });
  return {
    schema_version: "gsgp.prospective.v1",
    generated_at: new Date().toISOString(),
    source_pr: sourcePr,
    records
  };
}

export function mockProspectivePayload(sourcePr) {
  return validateProspectivePayload({
    records: [{
      algorithm_id: "sbayesrc",
      dataset_id: "ukb",
      expected: 92,
      confidence: "medium_high",
      estimate_label: "最有利",
      expected_metrics: { pearson: "0.45-0.65", r2: "0.18-0.42", auc: null, runtime: null },
      tool_status: "unverified",
      validation_status: "pending_validation",
      reasoning: {
        summary: "Mock 预审：UKB 的大样本欧洲祖先设定与 SBayesRC 论文主线最匹配。",
        evidence: ["论文在 UKB 完成 28 个近似独立性状的十折交叉验证。"],
        risks: ["论文使用约 7M SNP 与 BaselineLD v2.2；本站 SNP 密度可能不同。"],
        verification_plan: ["固定 SNP、注释、LD 参考和 split，由独立 runner 计算真实指标。"]
      }
    }]
  }, sourcePr);
}

async function callModel(pr) {
  if (!process.env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY is required unless --mock is used.");
  const base = String(process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/\/+$/, "");
  const endpoint = base.endsWith("/chat/completions") ? base : `${base}/chat/completions`;
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";
  const system = `你是 GSGP-Bench 的论文预审代理。你只根据用户提供的 PR 标题、正文和 diff 生成“运行前预期”，不得声称已经运行或复现。
输出必须是一个 JSON 对象，且只能使用给定 algorithm_id 和 dataset_id。
每条 record 必须包含 algorithm_id、dataset_id、expected(0-100 整数)、confidence(low|low_medium|medium|medium_high|high)、estimate_label、expected_metrics、tool_status=unverified、validation_status=pending_validation、reasoning。
reasoning 必须包含 summary、evidence、risks、verification_plan 四个字段；evidence 必须引用论文、文档、代码或 PR 中可核验的内容；verification_plan 必须写出怎样用真实数据和独立 runner 验证。
如果 PR 没有足够论文/数据依据，给出低 confidence，并明确风险，不要编造结果。`;
  const user = `allowed algorithm_id: ${ALGORITHMS.join(", ")}
allowed dataset_id: ${DATASETS.join(", ")}

PR URL: ${pr.url}
PR title: ${pr.title}
PR body:
${pr.body.slice(0, 30_000)}

PR diff:
${pr.diff}`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      "content-type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0.1,
      response_format: { type: "json_object" },
      messages: [{ role: "system", content: system }, { role: "user", content: user }]
    })
  });
  if (!response.ok) throw new Error(`Model request failed: ${response.status} ${(await response.text()).slice(0, 300)}`);
  const data = await response.json();
  return extractJson(data?.choices?.[0]?.message?.content);
}

async function main() {
  const args = process.argv.slice(2);
  const getArg = (name, fallback = null) => {
    const index = args.indexOf(name);
    return index >= 0 ? args[index + 1] : fallback;
  };
  const mock = args.includes("--mock") || process.env.PROSPECTIVE_MOCK === "1";
  const inputPath = getArg("--input");
  const prUrl = getArg("--pr");
  const outPath = path.resolve(getArg("--out", DEFAULT_OUT));
  if (!inputPath && !prUrl) throw new Error("Provide --pr <github PR URL> or --input <json file>.");

  const pr = inputPath
    ? JSON.parse(await readFile(path.resolve(inputPath), "utf8"))
    : await fetchPrInput(prUrl);
  const sourcePr = {
    url: pr.url || pr.html_url || prUrl || "local-input",
    title: pr.title || "Untitled PR",
    head_sha: pr.head_sha || pr.head?.sha || "unknown",
    author: pr.author || pr.user?.login || null
  };
  const payload = mock ? mockProspectivePayload(sourcePr) : validateProspectivePayload(await callModel(pr), sourcePr);
  await mkdir(path.dirname(outPath), { recursive: true });
  await writeFile(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(`Wrote ${outPath}`);
  console.log(`Records: ${payload.records.length}; all pending_validation / unverified.`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
