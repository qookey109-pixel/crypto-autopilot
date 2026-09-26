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

  await expect(page).toHaveTitle(/Qookey Crypto Autopilot/);
  await expect(page.locator(".paper-pill")).toContainText("PAPER / LIVE-PAPER");
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
