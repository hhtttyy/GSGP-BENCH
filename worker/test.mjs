import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import worker from "./index.js";

const assetFetcher = {
  fetch: async () => new Response("<!doctype html><title>asset</title>", {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8" }
  })
};

const mockEnv = { ASSETS: assetFetcher, AI_MOCK: "1" };
const realEnv = {
  ASSETS: assetFetcher,
  AI_MOCK: "0",
  OPENAI_API_KEY: "test-key",
  OPENAI_BASE_URL: "https://ai.example/v1",
  OPENAI_MODEL: "test-model"
};
const allowedMethods = JSON.parse(readFileSync(new URL("../site/data/catalog/allowed-methods.json", import.meta.url), "utf8"));
const prospectiveEnv = { ...mockEnv, ALLOWED_METHODS: JSON.stringify(allowedMethods) };

const validPayload = {
  metric: "Pearson r（越高越好）",
  algorithms: ["GBLUP / rrBLUP", "IFAM"],
  datasets: ["GSGP-Sim 500×5k"],
  cells: [
    { algorithm: "GBLUP / rrBLUP", dataset: "GSGP-Sim 500×5k", status: "探索", value: 0.5075, sd: null },
    { algorithm: "IFAM", dataset: "GSGP-Sim 500×5k", status: "流程测试", value: -0.032, sd: null }
  ],
  pageNotes: ["探索不是正式复现。", "流程测试不能作为科学结果。"]
};

function analyzeRequest(body = validPayload, headers = {}) {
  return new Request("https://bench.example/api/analyze", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body)
  });
}

const validProspective = {
  method_name: "BayesR",
  repo_url: "https://github.com/syntheke/bayesR",
  paper_url: "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1004969"
};

function prospectiveRequest(body = validProspective, headers = {}) {
  return new Request("https://bench.example/api/prospective", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: typeof body === "string" ? body : JSON.stringify(body)
  });
}

test("mock mode returns a labelled local analysis", async () => {
  const response = await worker.fetch(analyzeRequest(), mockEnv);
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type"), /application\/json/);
  const data = await response.json();
  assert.equal(data.mock, true);
  assert.equal(data.model, "mock");
  assert.match(data.text, /本地 Mock 解读/);
  assert.match(data.text, /2 个结果单元/);
  assert.match(data.text, /探索 1，流程测试 1/);
});

test("prospective mock returns only pending records and a catalog card", async () => {
  const response = await worker.fetch(prospectiveRequest(), prospectiveEnv);
  assert.equal(response.status, 200);
  const data = await response.json();
  assert.equal(data.mock, true);
  assert.equal(data.model, "mock");
  assert.equal(data.algorithm.id, "bayesr");
  assert.equal(data.algorithm.status, "converting");
  assert.equal(data.algorithm.statusLabel, "待认证");
  assert.equal(data.records.length, 5);
  for (const record of data.records) {
    assert.equal(record.tool_status, "unverified");
    assert.equal(record.validation_status, "pending_validation");
    assert.equal(record.source_submission.hook, "allowed-methods.v1");
  }
});

test("prospective rejects a paper URL outside the allowlist", async () => {
  const response = await worker.fetch(prospectiveRequest({
    ...validProspective,
    paper_url: "https://example.com/not-bayesr"
  }), prospectiveEnv);
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, "PAPER_MISMATCH");
});

test("prospective rejects known methods without auto-submit", async () => {
  const response = await worker.fetch(prospectiveRequest({
    method_name: "BayesB",
    repo_url: "https://github.com/example/bayesb",
    paper_url: "https://academic.oup.com/genetics/article/157/4/1819/6049921"
  }), prospectiveEnv);
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error.code, "METHOD_REQUIRES_REVIEW");
});

test("prospective requires a GitHub repository URL", async () => {
  const response = await worker.fetch(prospectiveRequest({
    ...validProspective,
    repo_url: "https://example.com/bayesr"
  }), prospectiveEnv);
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, "INVALID_PAYLOAD");
});

test("prospective rejects non-POST and cross-origin calls", async () => {
  const nonPost = await worker.fetch(new Request("https://bench.example/api/prospective"), prospectiveEnv);
  assert.equal(nonPost.status, 405);
  assert.equal((await nonPost.json()).error.code, "METHOD_NOT_ALLOWED");

  const crossOrigin = await worker.fetch(
    prospectiveRequest(validProspective, { origin: "https://evil.example" }),
    prospectiveEnv
  );
  assert.equal(crossOrigin.status, 403);
  assert.equal((await crossOrigin.json()).error.code, "FORBIDDEN_ORIGIN");
});

test("prospective real mode uses the model but keeps pending status", async () => {
  const originalFetch = globalThis.fetch;
  let sent = null;
  globalThis.fetch = async (_url, options) => {
    sent = JSON.parse(options.body);
    return new Response(JSON.stringify({
      choices: [{ message: { content: JSON.stringify({
        summary: "AI 预审摘要",
        evidence: ["论文提出混合先验"],
        risks: ["尚未真实运行"],
        verification_plan: ["固定 split 后由独立 runner 运行"]
      }) } }]
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const response = await worker.fetch(prospectiveRequest(), {
      ...realEnv,
      ALLOWED_METHODS: JSON.stringify(allowedMethods)
    });
    assert.equal(response.status, 200);
    const data = await response.json();
    assert.equal(data.mock, false);
    assert.equal(data.model, "test-model");
    assert.equal(data.records[0].reasoning.summary, "AI 预审摘要");
    assert.equal(data.records[0].tool_status, "unverified");
    assert.match(sent.messages[0].content, /不能声称已运行/);
    assert.deepEqual(sent.response_format, { type: "json_object" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("non-POST requests are rejected", async () => {
  const response = await worker.fetch(
    new Request("https://bench.example/api/analyze"),
    mockEnv
  );
  assert.equal(response.status, 405);
  assert.equal((await response.json()).error.code, "METHOD_NOT_ALLOWED");
});

test("cross-origin browser calls are rejected", async () => {
  const response = await worker.fetch(
    analyzeRequest(validPayload, { origin: "https://evil.example" }),
    mockEnv
  );
  assert.equal(response.status, 403);
  assert.equal((await response.json()).error.code, "FORBIDDEN_ORIGIN");
});

test("same-origin browser calls are accepted", async () => {
  const response = await worker.fetch(
    analyzeRequest(validPayload, { origin: "https://bench.example" }),
    mockEnv
  );
  assert.equal(response.status, 200);
});

test("malformed JSON is rejected", async () => {
  const response = await worker.fetch(analyzeRequest("{not json"), mockEnv);
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, "INVALID_PAYLOAD");
});

test("empty cells are rejected", async () => {
  const response = await worker.fetch(analyzeRequest({ metric: "Pearson r", cells: [] }), mockEnv);
  assert.equal(response.status, 400);
  assert.equal((await response.json()).error.code, "INVALID_PAYLOAD");
});

test("oversized bodies are rejected", async () => {
  const response = await worker.fetch(analyzeRequest("x".repeat(24_001)), mockEnv);
  assert.equal(response.status, 413);
  assert.equal((await response.json()).error.code, "PAYLOAD_TOO_LARGE");
});

test("missing API key is reported, not silently mocked", async () => {
  const response = await worker.fetch(analyzeRequest(), { ASSETS: assetFetcher, AI_MOCK: "0" });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, "AI_NOT_CONFIGURED");
});

test("upstream request shape and response are handled", async () => {
  const originalFetch = globalThis.fetch;
  let seen = null;
  globalThis.fetch = async (url, options) => {
    seen = { url: String(url), options };
    return new Response(JSON.stringify({
      model: "test-model-2026",
      choices: [{ message: { content: "第一项观察。\n第二项观察。" } }],
      usage: { total_tokens: 42 }
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const response = await worker.fetch(analyzeRequest(), realEnv);
    assert.equal(response.status, 200);
    const data = await response.json();
    assert.equal(data.text, "第一项观察。\n第二项观察。");
    assert.equal(data.model, "test-model-2026");
    assert.equal(data.mock, false);
    assert.deepEqual(data.usage, { total_tokens: 42 });

    assert.equal(seen.url, "https://ai.example/v1/chat/completions");
    assert.equal(seen.options.method, "POST");
    assert.equal(seen.options.headers.authorization, "Bearer test-key");
    const sent = JSON.parse(seen.options.body);
    assert.equal(sent.model, "test-model");
    assert.equal(sent.temperature, 0.2);
    assert.equal(sent.max_tokens, 700);
    assert.match(sent.messages[0].content, /不能编造/);
    assert.match(sent.messages[1].content, /GSGP-Sim 500×5k/);
    assert.match(sent.messages[1].content, /流程测试/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("Qwen thinking can be disabled through an opt-in env flag", async () => {
  const originalFetch = globalThis.fetch;
  let sent = null;
  globalThis.fetch = async (_url, options) => {
    sent = JSON.parse(options.body);
    return new Response(JSON.stringify({
      choices: [{ message: { content: "ok" } }]
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const response = await worker.fetch(analyzeRequest(), {
      ...realEnv,
      AI_DISABLE_THINKING: "1"
    });
    assert.equal(response.status, 200);
    assert.equal(sent.enable_thinking, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("a base URL already ending in /chat/completions is not duplicated", async () => {
  const originalFetch = globalThis.fetch;
  let seenUrl = "";
  globalThis.fetch = async (url) => {
    seenUrl = String(url);
    return new Response(JSON.stringify({
      choices: [{ message: { content: "ok" } }]
    }), { status: 200, headers: { "content-type": "application/json" } });
  };
  try {
    const response = await worker.fetch(analyzeRequest(), {
      ...realEnv,
      OPENAI_BASE_URL: "https://ai.example/v1/chat/completions"
    });
    assert.equal(response.status, 200);
    assert.equal(seenUrl, "https://ai.example/v1/chat/completions");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("upstream errors are sanitized", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response("upstream says no", { status: 401 });
  try {
    const response = await worker.fetch(analyzeRequest(), realEnv);
    assert.equal(response.status, 502);
    const data = await response.json();
    assert.equal(data.error.code, "AI_UPSTREAM_ERROR");
    assert.doesNotMatch(data.error.message, /upstream says no/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("empty upstream content is reported", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    choices: [{ message: { content: "   " } }]
  }), { status: 200, headers: { "content-type": "application/json" } });
  try {
    const response = await worker.fetch(analyzeRequest(), realEnv);
    assert.equal(response.status, 502);
    assert.equal((await response.json()).error.code, "AI_EMPTY_RESPONSE");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("network failures are reported", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("network down");
  };
  try {
    const response = await worker.fetch(analyzeRequest(), realEnv);
    assert.equal(response.status, 502);
    assert.equal((await response.json()).error.code, "AI_REQUEST_FAILED");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("unknown API routes return JSON 404", async () => {
  const response = await worker.fetch(
    new Request("https://bench.example/api/unknown"),
    mockEnv
  );
  assert.equal(response.status, 404);
  assert.equal((await response.json()).error.code, "NOT_FOUND");
});

test("everything else falls through to static assets", async () => {
  const response = await worker.fetch(
    new Request("https://bench.example/resources/methods/index.html"),
    mockEnv
  );
  assert.equal(response.status, 200);
  assert.match(await response.text(), /asset/);
});
