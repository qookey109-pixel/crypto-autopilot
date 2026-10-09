const { test, expect } = require("@playwright/test");

const EXPECTED_VIEWS = [
  ["overview", "總覽"],
  ["data-health", "資料健康度"],
  ["signals", "交易訊號"],
  ["strategy", "策略"],
  ["positions", "模擬持倉"],
  ["trades", "模擬交易"],
  ["performance", "績效中心"],
  ["backtests", "回測"],
  ["gates", "風險與閘門"],
];

const SAFE_BOUNDARY = {
  providerReadsPerformed: false,
  r2ReadsPerformed: false,
  r2WritesPerformed: false,
  artifactReadsPerformed: false,
  logReadsPerformed: false,
  holdoutAccessed: false,
  sourceSwitchAuthorized: false,
  tradePlanAuthorized: false,
  realMoneyOrderAuthorized: false,
  liveTradingAuthorized: false,
};

test("dashboard loads governed data and all primary views", async ({ page, baseURL }) => {
  const pageErrors = [];
  const badResponses = [];
  const normalizedBaseURL = new URL(baseURL).href;
  page.on("pageerror", error => pageErrors.push(error.message));
  page.on("response", response => {
    if (response.status() >= 400 && response.url().startsWith(normalizedBaseURL)) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  await page.goto(baseURL, { waitUntil: "networkidle" });

  const skipLink = page.locator(".skip-link");
  await expect(skipLink).toHaveAttribute("href", "#top");
  await skipLink.focus();
  await expect(skipLink).toBeFocused();

  await expect(page).toHaveTitle(/Qookey Crypto Autopilot/);
  await expect(page.locator(".paper-pill")).toContainText("PAPER / LIVE-PAPER");
  await expect(page.locator(".home-details").first()).toHaveAttribute("open", "");
  await expect(page.locator("#refresh-button")).toBeEnabled();
  await expect(page.locator("#snapshot-label")).not.toHaveText("狀態快照暫時無法讀取");
  await expect(page.locator("#pipeline-list")).not.toBeEmpty();
  await expect(page.locator("#home-history-state")).toHaveText("10/10 分片 · COMPLETE");
  await expect(page.locator("#home-history-detail")).toContainText("Core100 歷史資料已完成");
  await expect(page.locator("#home-history-state")).not.toContainText("8/10");
  await expect(page.locator("#home-history-source")).toHaveAttribute(
    "href",
    "https://github.com/qookey109-pixel/crypto-autopilot/blob/main/CURRENT_STATUS.md"
  );
  await expect(page.locator("#readiness-heading")).not.toContainText("9/16");

  for (const [view, title] of EXPECTED_VIEWS) {
    const button = page.locator(`.nav-item[data-view="${view}"]`);
    await button.scrollIntoViewIfNeeded();
    await button.click();
    await expect(page.locator("#page-title")).toHaveText(title);
    await expect(page.locator(`#view-${view}`)).toBeVisible();
  }

  await page.locator('.nav-item[data-view="overview"]').click();
  await page.locator("#refresh-button").click();
  await expect(page.locator("#refresh-button")).toBeEnabled();
  await expect(page.locator("#page-title")).toHaveText("總覽");

  expect(pageErrors).toEqual([]);
  expect(badResponses).toEqual([]);
});

test("VNext market research is clearly non-live and fits a 390px phone", async ({ page, baseURL }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(baseURL, { waitUntil: "networkidle" });
  const panel = page.locator("#vnext-market-heading").locator("xpath=ancestor::section[1]");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("雙批研究驗證 · 非即時");
  await expect(panel).toContainText("5 個市場各 240 根");
  await expect(panel).toContainText("936 根重疊 K 線一致");
  await expect(panel).toContainText("暖機 2/21 不足");
  await expect(panel).toContainText("兩批研究驗證 PASS（僅完整性）");
  await expect(panel.locator('a[href*="/actions/runs/37882460289"]')).toBeVisible();
  await expect(panel).toContainText("NOT_RUN（非 NO_TRADE）");
  await expect(panel).toContainText("來源 K 線時間");
  await expect(panel).toContainText("UNKNOWN");
  const researchContext = panel.locator("details.vnext-context-disclosure");
  await expect(researchContext).not.toHaveAttribute("open", "");
  await researchContext.locator("summary").focus();
  await page.keyboard.press("Enter");
  await expect(researchContext).toHaveAttribute("open", "");
  await expect(researchContext).toContainText("5 個研究市場 · 非排名");
  await expect(researchContext).toContainText("REGIME_UNAVAILABLE");
  await expect(researchContext).toContainText("研究 Radar");
  const bounds = await panel.boundingBox();
  expect(bounds).not.toBeNull();
  expect(bounds.x).toBeGreaterThanOrEqual(-1);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(391);

  const links = page.locator(".external-research-links a");
  await expect(links).toHaveCount(4);
  for (const link of await links.all()) {
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", "noopener noreferrer");
  }
});

test("served dashboard content hash matches the exact build", async ({ request, baseURL }) => {
  const expected = process.env.PLAYWRIGHT_EXPECTED_CONTENT_HASH;
  test.skip(!expected, "PLAYWRIGHT_EXPECTED_CONTENT_HASH is not set outside CI");
  expect(expected).toMatch(/^[0-9a-f]{64}$/);

  await expect.poll(async () => {
    const url = new URL("data/content-hash.txt", baseURL);
    url.searchParams.set("qa", String(Date.now()));
    const response = await request.get(url.href, {
      headers: { "cache-control": "no-cache" },
    });
    if (!response.ok()) return `HTTP ${response.status()}`;
    return (await response.text()).trim();
  }, {
    timeout: 30_000,
    intervals: [500, 1_000, 2_000],
  }).toBe(expected);
});

test("stale cloud metadata is labeled stale and keeps only safe evidence links", async ({ page, baseURL }) => {
  const observedAtUtc = new Date(Date.now() - 31 * 60 * 60 * 1000).toISOString();
  const cloud = {
    schema: "qookey-cloud-run-status-v0.2",
    authority: false,
    mode: "GITHUB_ACTIONS_METADATA_ONLY",
    observedAtUtc,
    summary: {
      repositoryCronDeclarationCount: 1,
      monitoredCronDeclarationCount: 1,
      currentEffectiveScheduleCount: 1,
      expiredScheduleCount: 0,
      pendingScheduleCount: 0,
      expiredFrozenCronDeclarationCount: 0,
    },
    items: [{
      operationId: "browser-contract-fixture",
      title: "Browser Contract Fixture",
      workflow: "dashboard-github-pages.yml",
      lifecycleState: "CURRENT_EFFECTIVE",
      authorityState: "ACTIVE",
      authorityPath: ".github/workflows/dashboard-github-pages.yml",
      authorityUrl: "https://github.com/qookey109-pixel/crypto-autopilot/blob/main/.github/workflows/dashboard-github-pages.yml",
      maxAgeSeconds: 108000,
      activeFromUtc: "2026-09-21T00:00:00Z",
      activeUntilUtc: null,
      latestAutomaticRun: {
        state: "WORKFLOW_SUCCESS",
        runId: 123,
        headSha: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        evidenceTimeUtc: observedAtUtc,
        workflowConclusion: "success",
        sourceUrl: "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/123",
      },
      freshnessState: "STALE",
      businessResult: {
        status: "UNKNOWN_FROM_GITHUB_RUN_METADATA",
        reason: "WORKFLOW_CONCLUSION_IS_NOT_BUSINESS_RESULT",
      },
    }],
    safetyBoundary: SAFE_BOUNDARY,
  };

  await page.route("**/data/cloud-runs.json", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(cloud),
  }));
  await page.goto(baseURL, { waitUntil: "networkidle" });

  await expect(page.locator("#cloud-run-updated")).toContainText("較舊快照");
  const links = page.locator("#cloud-run-list .cloud-run-links a");
  await expect(links).toHaveCount(2);
  await expect(links.nth(0)).toHaveAttribute(
    "href",
    "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/123"
  );
  await expect(links.nth(1)).toHaveAttribute(
    "href",
    "https://github.com/qookey109-pixel/crypto-autopilot/blob/main/.github/workflows/dashboard-github-pages.yml"
  );
  await expect(links.nth(0)).toHaveAttribute("rel", "noopener noreferrer");
  await expect(links.nth(1)).toHaveAttribute("rel", "noopener noreferrer");
});

test("dashboard snapshot fetch failure fails closed without disabling refresh", async ({ page, baseURL }) => {
  await page.route("**/data/dashboard.json", route => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ error: "simulated dashboard snapshot failure" }),
  }));

  await page.goto(baseURL, { waitUntil: "networkidle" });

  await expect(page.locator("#snapshot-label")).toHaveText("狀態快照暫時無法讀取");
  await expect(page.locator("#refresh-button")).toBeEnabled();
  await expect(page.locator("#cloud-run-updated")).toContainText("暫不可核實");
  await expect(page.locator("#market-count")).toHaveText("—");
  await expect(page.locator("#funding-months")).toHaveText("—");
});

test("alternative-assets projection failure stays unknown instead of zero", async ({ page, baseURL }) => {
  await page.route("**/data/alternative-assets.json", route => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ error: "simulated alternative-assets failure" }),
  }));

  await page.goto(baseURL, { waitUntil: "networkidle" });

  for (const id of [
    "alternative-assets-candidates",
    "alternative-assets-matched",
    "alternative-assets-equity",
    "alternative-assets-funds",
    "alternative-assets-metals",
    "alternative-assets-capacity",
  ]) {
    await expect(page.locator(`#${id}`)).toHaveText("—");
  }
  await expect(page.locator("#alternative-assets-observed-at")).toContainText("暫不可核實");
  await expect(page.locator("#alternative-assets-note")).toContainText("不以 0 代替缺少資料");
});

test("paper equity chart renders only from explicit paper evidence", async ({ page, baseURL }) => {
  const observedAtUtc = new Date(Date.now() - 60_000).toISOString();
  const paper = {
    schema: "pionex-public-paper-training-run-v0.1",
    status: "READY",
    mode: "PAPER_TRAINING_ONLY",
    runId: "browser-chart-fixture",
    observedAtUtc,
    authority: {
      publicMarketDataReadAuthorized: false,
      paperCandidateGenerationAuthorized: false,
      repositoryPaperBrokerAuthorized: true,
      formalTradePlanAuthorized: false,
      pionexDemoAutomationAuthorized: false,
      privateApiUsed: false,
      r2ReadsPerformed: false,
      r2WritesPerformed: false,
      holdoutAccessed: false,
      sourceSwitchAuthorized: false,
      realMoneyOrderAuthorized: false,
      liveTradingAuthorized: false,
    },
    latestCandidates: [],
    paperTrades: [],
    trainingRecords: [],
    manualPionexDemoSamples: [],
    equityCurve: [100, 101.5, 99.25, 103],
    metrics: {
      trade_count: 3,
      win_count: 2,
      loss_count: 1,
      win_rate: 2 / 3,
      net_pnl_usd: 3,
      return_pct: 3,
      max_drawdown_pct: 2.2,
      profit_factor: 1.8,
      trade_sharpe: null,
      total_fees_usd: 0.1,
      total_funding_usd: 0,
      total_slippage_cost_usd: 0.1,
    },
    interpretation: "Browser-only paper evidence fixture.",
  };

  await page.route("**/data/paper-training.json", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(paper),
  }));
  await page.goto(baseURL, { waitUntil: "networkidle" });

  const chart = page.locator("#paper-equity-chart");
  await expect(chart).not.toHaveClass(/no-data/);
  await expect(chart).toHaveAttribute("aria-label", "模擬資產曲線，共 4 個已記錄節點");
  await expect(page.locator("#paper-equity-line")).not.toHaveAttribute("d", "M0 150 H800");
  await expect(page.locator("#paper-equity-note")).toContainText("4 個已記錄節點");
});


test("cloud paper dashboard shows inactive state without inventing account evidence", async ({ page, baseURL }) => {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.locator("#cloud-paper-status")).toHaveText("已實作 · 尚未啟用");
  await expect(page.locator("#cloud-paper-last-run")).toHaveText("尚未執行");
  await expect(page.locator("#cloud-paper-candidates")).toHaveText("尚未執行 · 空策略登錄，沒有合格候選");
  await expect(page.locator("#cloud-paper-regime")).toHaveText("REGIME_UNAVAILABLE · 缺 TOTAL3 / BTC dominance；23 市場 breadth 覆蓋未驗證");
  await expect(page.locator(".cloud-paper-panel")).toContainText("固定 23 市場 breadth 成員已準備，歷史覆蓋仍未驗證");
  await expect(page.locator("#cloud-paper-account")).toHaveText("尚未初始化");
  await expect(page.locator("#cloud-paper-budget")).toHaveText("BLOCKED_BUDGET · V0.3 部分用量證據待查");
  await expect(page.locator("#cloud-paper-storage-capacity")).toHaveText("部分觀測 616,541,780 bytes（1 bucket）· 完整用量/headroom 未知 · 硬停 8.0 GB");
  await expect(page.locator("#cloud-paper-trace-status")).toHaveText("尚無正式循環報告");
  await expect(page.locator("#cloud-paper-trace-detail")).toContainText("最新正式 run 為 NOT_RUN");
  await expect(page.locator(".cloud-paper-panel")).toContainText("API key");
  await expect(page.locator(".cloud-paper-panel")).toContainText("D1 migrations 尚未套用且 D1 未 provision");
  await expect(page.locator(".cloud-paper-panel")).toContainText("未知值不顯示成 0");
});

const cloudPaperProjection = require("../../web/data/cloud-paper-loop.json");
const legacyCloudPaperProjection = {
  "schema": "qookey-cloud-paper-dashboard-v0.1",
  "authority": false,
  "mode": "PAPER_AND_LIVE_PAPER_ONLY",
  "evidence_basis_main_sha": "b2f0a1e2b4129cff207f6b9c59d395ecc705aaab",
  "observed_at_utc": "2026-09-29T14:41:00.239158Z",
  "activation": {
    "enabled": false,
    "status": "BLOCKED"
  },
  "latest_run": {
    "status": "NOT_RUN",
    "run_id": null,
    "attempt": null,
    "head_sha": null,
    "report_status": null,
    "report_artifact": null,
    "decision_trace_status": "NOT_AVAILABLE_NO_OFFICIAL_RUN"
  },
  "strategy": {
    "registry_status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
    "eligible_count": 0,
    "empty_registry_result": "NO_TRADE",
    "runtime_result": "NOT_RUN_NO_FORMAL_NO_TRADE_RESULT"
  },
  "market": {
    "provider": "PIONEX_PUBLIC",
    "macro_regime": "REGIME_UNAVAILABLE",
    "unavailable_fields": [
      "TOTAL3",
      "BTC_DOMINANCE",
      "ALIGNED_BREADTH"
    ],
    "provider_fallback": false,
    "pionex_public_market_data_api_key_required": false,
    "breadth_coverage": {
      "candidate_market_count": 23,
      "minimum_required_market_count": 20,
      "membership_state": "PREPARED_CANDIDATE_MEMBERSHIP_ONLY_COVERAGE_UNVERIFIED",
      "coverage_verified": false
    }
  },
  "account": {
    "initialized": false,
    "planned_initial_equity_usd": 10000,
    "confirmed_equity_usd": null,
    "open_position_count": null,
    "realized_pnl_usd": null,
    "unrealized_pnl_usd": null
  },
  "budget": {
    "monthly_budget_usd": 0,
    "account_wide_usage_evidence": "REVIEW_REQUIRED_V0_2_DATASET_COVERAGE_INCOMPLETE",
    "reservation_guard": "PROVIDER_R2_GUARD_IMPLEMENTED_RUNTIME_NOT_ACTIVATED",
    "state": "BLOCKED_BUDGET",
    "d1_reservation_ledger": "SHARED_LEDGER_CODE_PREPARED_MIGRATIONS_NOT_APPLIED_D1_NOT_PROVISIONED",
    "d1_free_tier_usage_evidence": "UNKNOWN_EMPTY_UNVERIFIED",
    "d1_storage_growth_bytes_per_statement": 16384,
    "d1_storage_growth_policy_bytes_per_utc_day": 12582912,
    "storage_capacity": {
      "state": "USAGE_PARTIAL_BLOCKED",
      "measured_storage_bytes": null,
      "usage_evidence": "PARTIAL_R2_EVIDENCE_NOT_ZERO_OR_COMPLETE",
      "report_object_max_bytes": 262144,
      "per_run_growth_max_bytes": 2097152,
      "per_utc_day_growth_max_bytes": 201326592,
      "max_31_day_growth_bytes": 6241124352,
      "warning_threshold_bytes": 6400000000,
      "hard_stop_bytes": 8000000000,
      "all_writer_coverage_proven": false
    },
    "usage_audit_evidence": {
      "authority": "cloud_paper_usage_audit_v0_2",
      "status": "REVIEW_REQUIRED",
      "reason_code": "DATASET_COVERAGE_INCOMPLETE",
      "run_id": 36584465739,
      "attempt": 1,
      "run_head_sha": "21d37a44c6f3c5bba340908705488a05e7a5f7c7",
      "artifact_id": 11041290995,
      "artifact_name": "cloud-paper-usage-audit-v0-2-36584465739-1",
      "artifact_sha256": "9ece6ff0a937f930d1137b2539052833bb5d94960dff8c1e50cce4cdbdadc258",
      "cloudflare_requests": 1,
      "d1_rows_state": "EMPTY_UNVERIFIED",
      "d1_storage_state": "EMPTY_UNVERIFIED",
      "r2_operations_state": "LIMIT_REACHED",
      "r2_operations_group_count": 10000,
      "r2_storage_state": "PRESENT",
      "r2_storage_group_count": 1297,
      "account_wide_cost": "UNKNOWN",
      "complete_storage_byte_aggregate": "UNKNOWN",
      "shared_writer_coverage": "UNKNOWN",
      "storage_headroom": "UNKNOWN",
      "conclusion": "R2 analytics are partial; zero cost and FREE-tier headroom are not established."
    },
    "zero_cost_conclusion": "UNKNOWN",
    "account_wide_writer_coverage": "UNKNOWN"
  },
  "model_quality": "REJECT",
  "boundary": {
    "paper_only": true,
    "real_money_orders": false,
    "live_trading": false,
    "holdout_access": false,
    "source_switch": false,
    "model_promotion": false
  },
  "production": {
    "entrypoint_workflow": "NOT_WIRED",
    "natural_schedule": "NOT_CONFIGURED"
  }
};

test("cloud paper V0.3 separates projection time, source time and partial bytes", async ({ page, baseURL }) => {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.locator("#cloud-paper-detail")).toContainText("125,309");
  await expect(page.locator("#cloud-paper-detail")).toContainText("D1 未查詢");
  await expect(page.locator("#cloud-paper-evidence-observed")).toContainText(cloudPaperProjection.observed_at_utc);
  await expect(page.locator("#cloud-paper-evidence-snapshot")).toContainText("2026-09-29T15:20:00Z");
  await expect(page.locator("#cloud-paper-evidence-snapshot")).toContainText("freshness 未知");
  await expect(page.locator("#cloud-paper-evidence-run")).toHaveAttribute("href",
    "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36593296360/artifacts/11045150561");
});

test("reviewed V0.2 historical projection remains readable", async ({ page, baseURL }) => {
  await page.route("**/data/cloud-paper-loop.json", route => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify(legacyCloudPaperProjection),
  }));
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.locator("#cloud-paper-status")).toHaveText("已實作 · 尚未啟用");
  await expect(page.locator("#cloud-paper-budget")).toHaveText("BLOCKED_BUDGET · V0.2 部分用量證據待查");
  await expect(page.locator("#cloud-paper-detail")).toContainText("10,000 組上限");
  await expect(page.locator("#cloud-paper-evidence-run")).toHaveAttribute("href",
    "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36584465739/artifacts/11041290995");
});

for (const [name, mutate] of [
  ["run identity", data => { data.budget.usage_audit_evidence.run_id += 1; }],
  ["artifact identity", data => { data.budget.usage_audit_evidence.artifact_name = "wrong"; }],
  ["artifact digest", data => { data.budget.usage_audit_evidence.artifact_sha256 = "0".repeat(64); }],
  ["attempt boolean", data => { data.budget.usage_audit_evidence.attempt = true; }],
  ["false PASS", data => { data.budget.usage_audit_evidence.status = "PASS"; }],
  ["false cost", data => { data.budget.zero_cost_conclusion = "PASS"; }],
  ["partial promoted to full", data => { data.budget.storage_capacity.measured_storage_bytes = 616541780; }],
  ["unknown account shown zero", data => { data.account.confirmed_equity_usd = 0; }],
  ["live flag", data => { data.boundary.live_trading = true; }],
  ["missing capacity", data => { delete data.budget.storage_capacity; }],
]) {
  test(`cloud paper rejects ${name} and clears evidence after refresh`, async ({ page, baseURL }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    await expect(page.locator("#cloud-paper-evidence-run")).toBeVisible();
    const data = structuredClone(cloudPaperProjection);
    mutate(data);
    await page.route("**/data/cloud-paper-loop.json", route => route.fulfill({
      status: 200, contentType: "application/json", body: JSON.stringify(data),
    }));
    await page.locator("#refresh-button").click();
    await expect(page.locator("#cloud-paper-status")).toHaveText("無法核實");
    await expect(page.locator("#cloud-paper-account")).toHaveText("未核實");
    await expect(page.locator("#cloud-paper-evidence-run")).toBeHidden();
    await expect(page.locator("#cloud-paper-evidence-run")).not.toHaveAttribute("href");
    await expect(page.locator("#cloud-paper-evidence-snapshot")).toHaveText("來源資料時間：未核實");
    await expect(page.locator("#refresh-button")).toBeEnabled();
  });
}

for (const [name, status, body] of [
  ["missing page", 404, "{}"],
  ["null projection", 200, "null"],
]) {
  test(`cloud paper ${name} stays unknown`, async ({ page, baseURL }) => {
    await page.route("**/data/cloud-paper-loop.json", route => route.fulfill({
      status, contentType: "application/json", body,
    }));
    await page.goto(baseURL, { waitUntil: "networkidle" });
    await expect(page.locator("#cloud-paper-status")).toHaveText("無法核實");
    await expect(page.locator("#cloud-paper-storage-capacity")).toHaveText("用量未知 · 不顯示為 0");
    await expect(page.locator("#cloud-paper-evidence-run")).toBeHidden();
  });
}

test("cloud paper readiness distinguishes engineering from five activation conditions", async ({ page, baseURL }) => {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.locator("#cloud-paper-readiness-status")).toHaveText("尚未啟用 · 5 項待完成");
  await expect(page.locator("#cloud-paper-readiness-list li")).toHaveCount(5);
  await expect(page.locator("#cloud-paper-readiness-list")).toContainText("未來新增服務須先登錄");
  await expect(page.locator("#cloud-paper-readiness-list")).toContainText("未證明不等於額度不足");
  await expect(page.locator("#cloud-paper-engineering")).toContainText("16 項整合測試通過");
  await expect(page.locator("#cloud-paper-engineering")).toContainText("未代表正式帳戶已執行");
  await expect(page.locator("#cloud-paper-runtime")).toContainText("正式循環未執行");
  await expect(page.locator("#cloud-paper-readiness-source")).toContainText("非行情或用量的新鮮度證據");
  await expect(page.locator("#cloud-paper-engineering-run")).toHaveAttribute("href",
    "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37094784992");
});

for (const [name, mutate] of [
  ["missing readiness", data => { delete data.cloudPaperReadiness; }],
  ["false production result", data => { data.cloudPaperReadiness.runtime.cycle = "NO_TRADE"; }],
  ["false account coverage", data => { data.cloudPaperReadiness.blockers[0].state = "PASS"; }],
  ["invalid CI identity", data => { data.cloudPaperReadiness.engineering.ci_run_id = true; }],
  ["unregistered future writer", data => { data.cloudPaperReadiness.future_writers_require_registration_before_first_write = false; }],
]) {
  test(`cloud paper readiness rejects ${name} on refresh`, async ({ page, baseURL }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    await expect(page.locator("#cloud-paper-engineering-run")).toBeVisible();
    await page.route("**/data/dashboard.json", async route => {
      const response = await route.fetch();
      const data = await response.json();
      mutate(data);
      await route.fulfill({ response, json: data });
    });
    await page.locator("#refresh-button").click();
    await expect(page.locator("#cloud-paper-readiness-status")).toHaveText("無法核實");
    await expect(page.locator("#cloud-paper-readiness-list li")).toHaveCount(0);
    await expect(page.locator("#cloud-paper-engineering")).toHaveText("工程驗收：未核實");
    await expect(page.locator("#cloud-paper-engineering-run")).toBeHidden();
    await expect(page.locator("#cloud-paper-engineering-run")).not.toHaveAttribute("href");
    await expect(page.locator("#refresh-button")).toBeEnabled();
  });
}

test("cloud paper readiness clears stale success when dashboard fetch fails", async ({ page, baseURL }) => {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.locator("#cloud-paper-engineering-run")).toBeVisible();
  await page.route("**/data/dashboard.json", route => route.fulfill({
    status: 503, contentType: "application/json", body: "{}",
  }));
  await page.locator("#refresh-button").click();
  await expect(page.locator("#cloud-paper-readiness-status")).toHaveText("無法核實");
  await expect(page.locator("#cloud-paper-readiness-list li")).toHaveCount(0);
  await expect(page.locator("#cloud-paper-runtime")).toHaveText("正式執行與排程：未核實");
  await expect(page.locator("#cloud-paper-engineering-run")).not.toHaveAttribute("href");
});
