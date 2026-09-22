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
