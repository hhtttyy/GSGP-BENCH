import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { runSubmissionHook } from "./prospective-from-submission.mjs";

const allowlist = JSON.parse(await readFile(new URL("../site/data/catalog/allowed-methods.json", import.meta.url), "utf8"));
const bayesrUrl = "https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1004969";

test("BayesR hook generates only pending prospective records", () => {
  const result = runSubmissionHook({
    allowlist,
    submission: { method: "BayesR", paper_url: bayesrUrl, datasets: ["sim1000g", "duroc"], submitted_by: "test" },
    now: "2026-10-30T00:00:00.000Z"
  });
  assert.equal(result.catalog.schema_version, "gsgp.algorithm-catalog.v1");
  assert.equal(result.catalog.algorithms[0].id, "bayesr");
  assert.equal(result.catalog.algorithms[0].status, "converting");
  assert.equal(result.prospective.records.length, 2);
  for (const record of result.prospective.records) {
    assert.equal(record.tool_status, "unverified");
    assert.equal(record.validation_status, "pending_validation");
    assert.ok(record.expected >= 0 && record.expected <= 100);
    assert.equal(record.source_submission.hook, "allowed-methods.v1");
  }
});

test("paper URL must match the allowlist", () => {
  assert.throws(() => runSubmissionHook({
    allowlist,
    submission: { method: "BayesR", paper_url: "https://example.com/not-bayesr", datasets: ["sim1000g"] }
  }), /paper_url/);
});

test("known but non-auto-submit methods are rejected", () => {
  assert.throws(() => runSubmissionHook({
    allowlist,
    submission: { method: "BayesB", paper_url: "https://academic.oup.com/genetics/article/157/4/1819/6049921", datasets: ["sim1000g"] }
  }), /not enabled for automatic pre-review/);
});

test("unknown methods are rejected", () => {
  assert.throws(() => runSubmissionHook({
    allowlist,
    submission: { method: "NotAMethod", paper_url: bayesrUrl, datasets: ["sim1000g"] }
  }), /not in the allowlist/);
});
