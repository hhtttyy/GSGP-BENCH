#!/usr/bin/env node
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { validateProspectivePayload } from "./prospective-from-pr.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DEFAULT_ALLOWLIST = path.join(ROOT, "site/data/catalog/allowed-methods.json");
const DEFAULT_OUT = path.join(ROOT, "site/data/prospective/submissions.json");
const DEFAULT_CATALOG_OUT = path.join(ROOT, "site/data/catalog/algorithms.json");

function normalizeText(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeUrl(value) {
  const url = new URL(value);
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

function normalizeDoi(value) {
  return normalizeText(value)
    .replace(/^https?:\/\/(dx\.)?doi\.org\//, "")
    .replace(/^doi:\s*/, "");
}

function urlMatchesPaper(input, paper) {
  let candidate;
  try {
    candidate = normalizeUrl(input);
  } catch {
    return false;
  }
  const expected = normalizeUrl(paper.url);
  if (candidate === expected) return true;
  const candidateDoi = normalizeDoi(input);
  const expectedDoi = normalizeDoi(paper.doi || paper.url);
  return Boolean(candidateDoi && expectedDoi && candidateDoi === expectedDoi);
}

function resolveMethod(allowlist, value) {
  const key = normalizeText(value);
  return allowlist.methods.find((method) => {
    const aliases = [method.id, method.name, ...(method.aliases || [])];
    return aliases.some((alias) => normalizeText(alias) === key);
  }) || null;
}

function buildCatalogEntry(method, paperUrl, now) {
  return {
    id: method.id,
    name: method.name,
    family: method.family,
    input: method.input,
    year: method.year,
    status: "converting",
    statusLabel: "待认证",
    color: method.color,
    note: method.note,
    catalog_source: "allowed-methods.hook",
    catalog_updated_at: now,
    resources: {
      paper: { href: paperUrl, tip: `${method.paper.citation || method.name} · 论文原文链接` },
      skill: { tip: "论文 Skill 尚未生成；当前只有允许清单和预审记录。" },
      mcp: { badge: "待认证", tip: "MCP 未认证：仅完成提交与预审，尚未运行真实引擎或人工验收。" }
    }
  };
}

function buildRecords(method, submission, now) {
  const datasets = Array.isArray(submission.datasets) && submission.datasets.length
    ? submission.datasets.map((item) => String(item))
    : (method.allowed_datasets || []);
  if (!datasets.length) throw new Error("submission.datasets is required when the allowlist has no default datasets.");
  return datasets.map((dataset_id) => {
    if (!method.allowed_datasets.includes(dataset_id)) {
      throw new Error(`dataset_id not allowed for ${method.name}: ${dataset_id}`);
    }
    const template = method.expected_by_dataset?.[dataset_id];
    if (!template) throw new Error(`No expected template configured for ${method.name} × ${dataset_id}.`);
    return {
      algorithm_id: method.id,
      dataset_id,
      expected: template.expected,
      confidence: template.confidence,
      estimate_label: template.estimate_label || "允许方法 · 待认证",
      expected_metrics: {
        pearson: template.pearson || null,
        r2: template.r2 || null,
        auc: template.auc || null,
        runtime: null
      },
      tool_status: "unverified",
      validation_status: "pending_validation",
      source_submission: {
        method_id: method.id,
        method_name: method.name,
        paper_url: submission.paper_url,
        submitted_by: submission.submitted_by || "anonymous",
        submitted_at: submission.submitted_at || now,
        hook: "allowed-methods.v1"
      },
      reasoning: method.reasoning
    };
  });
}

export function runSubmissionHook({ allowlist, submission, now = new Date().toISOString() }) {
  if (!allowlist || allowlist.schema_version !== "gsgp.allowed-methods.v1" || !Array.isArray(allowlist.methods)) {
    throw new Error("Invalid allowed-methods schema.");
  }
  if (!submission || !submission.method || !submission.paper_url) {
    throw new Error("submission.method and submission.paper_url are required.");
  }
  const method = resolveMethod(allowlist, submission.method);
  if (!method) throw new Error(`method is not in the allowlist: ${submission.method}`);
  if (!method.auto_submit) {
    throw new Error(`method is known but not enabled for automatic pre-review: ${method.name}. Add an expected template and set auto_submit=true before using this hook.`);
  }
  if (!method.paper || !method.paper.url) throw new Error(`allowlist entry for ${method.name} has no paper URL.`);
  if (!urlMatchesPaper(submission.paper_url, method.paper)) {
    throw new Error(`submission.paper_url does not match the allowlist paper for ${method.name}.`);
  }

  const records = buildRecords(method, submission, now);
  const raw = {
    schema_version: "gsgp.prospective.v1",
    generated_at: now,
    source_pr: null,
    records
  };
  const validated = validateProspectivePayload(raw, null);

  const catalog = {
    schema_version: "gsgp.algorithm-catalog.v1",
    generated_at: now,
    algorithms: [buildCatalogEntry(method, submission.paper_url, now)]
  };
  return { catalog, prospective: validated };
}

function mergeProspective(existing, incoming) {
  const base = existing && existing.schema_version === "gsgp.prospective.v1"
    ? existing
    : { schema_version: "gsgp.prospective.v1", generated_at: incoming.generated_at, source_pr: null, records: [] };
  const key = (record) => `${record.algorithm_id}|${record.dataset_id}`;
  const incomingKeys = new Set(incoming.records.map(key));
  const kept = (base.records || []).filter((record) => !incomingKeys.has(key(record)));
  return {
    ...base,
    generated_at: incoming.generated_at,
    records: [...kept, ...incoming.records]
  };
}

function mergeCatalog(existing, incoming) {
  const base = existing && existing.schema_version === "gsgp.algorithm-catalog.v1"
    ? existing
    : { schema_version: "gsgp.algorithm-catalog.v1", generated_at: incoming.generated_at, algorithms: [] };
  const incomingIds = new Set(incoming.algorithms.map((item) => item.id));
  const kept = (base.algorithms || []).filter((item) => !incomingIds.has(item.id));
  return {
    ...base,
    generated_at: incoming.generated_at,
    algorithms: [...kept, ...incoming.algorithms]
  };
}

async function readJson(file) {
  try {
    return JSON.parse(await readFile(file, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

async function writeJson(file, payload) {
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

async function main() {
  const args = process.argv.slice(2);
  const getArg = (name, fallback = null) => {
    const index = args.indexOf(name);
    return index >= 0 ? args[index + 1] : fallback;
  };
  const submissionPath = getArg("--submission");
  if (!submissionPath) throw new Error("Provide --submission <json file>.");
  const allowlistPath = path.resolve(getArg("--allowlist", DEFAULT_ALLOWLIST));
  const outPath = path.resolve(getArg("--out", DEFAULT_OUT));
  const catalogOutPath = path.resolve(getArg("--catalog-out", DEFAULT_CATALOG_OUT));

  const submission = JSON.parse(await readFile(path.resolve(submissionPath), "utf8"));
  const allowlist = JSON.parse(await readFile(allowlistPath, "utf8"));
  const { catalog, prospective } = runSubmissionHook({ allowlist, submission });
  const mergedProspective = mergeProspective(await readJson(outPath), prospective);
  const mergedCatalog = mergeCatalog(await readJson(catalogOutPath), catalog);

  await writeJson(outPath, mergedProspective);
  await writeJson(catalogOutPath, mergedCatalog);
  console.log(`Wrote ${outPath}`);
  console.log(`Wrote ${catalogOutPath}`);
  console.log(`Hook: allowed ${submission.method}; records=${prospective.records.length}; status=pending_validation/unverified.`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
