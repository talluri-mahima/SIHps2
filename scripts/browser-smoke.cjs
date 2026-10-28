const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const { createRequire } = require("node:module");
const load = createRequire(path.resolve(__dirname, "../web/package.json"));
const { chromium } = process.env.AICTE_PLAYWRIGHT_MODULE
  ? require(process.env.AICTE_PLAYWRIGHT_MODULE)
  : load("playwright");
const root = path.resolve(__dirname, "..");
const base = process.env.AICTE_TEST_URL || "http://127.0.0.1:8765";

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.AICTE_BROWSER_PATH
      ? { executablePath: process.env.AICTE_BROWSER_PATH }
      : {}),
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true,
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const checks = [];
  const record = (name) => checks.push({ name, status: "PASS" });
  try {
    await page.goto(base);
    await page.getByRole("button", { name: "Scrutiny officer" }).click();
    await page.getByRole("heading", { name: "Application overview" }).waitFor();
    await page.locator("#application-select").waitFor();
    await page
      .locator("#application-select")
      .selectOption({ label: "Example Institute of Technology" });
    await page.getByText("5 / 5", { exact: true }).waitFor();
    assert.match(
      await page.locator("#application-select option:checked").textContent(),
      /Example Institute of Technology/,
    );
    record("officer opens assigned application");
    await page.getByRole("button", { name: "Evidence", exact: true }).click();
    await page.getByRole("heading", { name: "Document inventory" }).waitFor();
    const documentButtons = page.locator(".doc-row");
    assert.equal(await documentButtons.count(), 5);
    for (let i = 0; i < 5; i++) {
      await documentButtons.nth(i).click();
      const image = page.locator(".paper img");
      await image.waitFor();
      await image.evaluate((img) =>
        img.complete
          ? Promise.resolve()
          : new Promise((resolve, reject) => {
              img.onload = resolve;
              img.onerror = reject;
            }),
      );
      assert(await image.evaluate((img) => img.naturalWidth > 0));
      const confirm = page.getByRole("button", {
        name: "Confirm displayed document facts",
      });
      if (await confirm.count()) {
        await confirm.click();
        await confirm.waitFor({ state: "detached" });
      }
    }
    record("five original PDF pages render and facts confirm");
    fs.mkdirSync(path.join(root, "reports", "screenshots"), {
      recursive: true,
    });
    await page.screenshot({
      path: path.join(root, "reports", "screenshots", "evidence.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Run evidence checks" }).click();
    await page
      .getByRole("status")
      .filter({ hasText: "Evidence checks completed" })
      .waitFor();
    await page
      .getByRole("button", { name: "Infrastructure", exact: true })
      .click();
    const floor2 = page.getByRole("row").filter({ hasText: "Floor 2" });
    await floor2.waitFor();
    assert.match(await floor2.innerText(), /Unknown/);
    assert.match(await floor2.innerText(), /Supported/);
    record(
      "second-floor occupancy remains unknown while fire scope is supported",
    );
    await page.screenshot({
      path: path.join(root, "reports", "screenshots", "infrastructure.png"),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Financial evidence", exact: true })
      .click();
    await page
      .getByRole("heading", {
        name: "Unrestricted funding claim requires bank confirmation",
      })
      .waitFor();
    assert.match(await page.locator(".finding-card").innerText(), /UNKNOWN/);
    record("lien reconciliation preserves unknown residual");
    await page
      .getByRole("button", { name: /Findings/ })
      .first()
      .click();
    const cards = page.locator(".finding-card");
    assert.equal(await cards.count(), 2);
    await cards
      .first()
      .getByRole("button", { name: "Review observation" })
      .click();
    await page
      .getByLabel("Reason / evidence response")
      .fill(
        "Reviewed synthetic original and accepted facts; documentary scope gap confirmed.",
      );
    await page.getByRole("button", { name: "Record review action" }).click();
    await page.getByRole("dialog").waitFor({ state: "detached" });
    await page
      .locator(".finding-card")
      .first()
      .getByText("Reviewer Confirmed", { exact: true })
      .waitFor();
    record("reviewer confirmation is persisted");
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Export confirmed observations" })
      .click();
    const download = await downloadPromise;
    const report = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
    assert.equal(report.report.confirmed_findings.length, 1);
    assert.equal(report.report.policy_status, "DRAFT_NOT_APPROVED");
    record(
      "download contains exactly the confirmed observation and draft-policy label",
    );
    await page.screenshot({
      path: path.join(root, "reports", "screenshots", "findings.png"),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Audit trail", exact: true })
      .click();
    await page.getByText("Chain intact", { exact: true }).waitFor();
    record("audit integrity verified in the interface");
    await page.locator(".switch-role select").selectOption("institution");
    await page.getByRole("button", { name: "New application" }).waitFor();
    await page.getByRole("button", { name: "New application" }).click();
    await page
      .getByLabel("Institution name")
      .fill("Browser test EoA institution");
    await page
      .getByRole("button", { name: "Create application", exact: true })
      .click();
    await page.getByRole("dialog").waitFor({ state: "detached" });
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await page.getByText("Prior EoA letter", { exact: true }).waitFor();
    record("applicant creates EoA application with its distinct checklist");
    await page.setViewportSize({ width: 390, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    );
    await page.screenshot({
      path: path.join(root, "reports", "screenshots", "mobile.png"),
      fullPage: true,
    });
    record("mobile overview has no horizontal page overflow");
    assert.deepEqual(errors, []);
    record("no uncaught browser errors");
    fs.writeFileSync(
      path.join(root, "reports", "browser-smoke.json"),
      JSON.stringify(
        { status: "PASS", at: new Date().toISOString(), base, checks, errors },
        null,
        2,
      ),
    );
    console.log(`${checks.length} browser workflow checks passed.`);
  } catch (error) {
    fs.mkdirSync(path.join(root, "reports"), { recursive: true });
    fs.writeFileSync(
      path.join(root, "reports", "browser-smoke.json"),
      JSON.stringify(
        { status: "FAIL", checks, error: String(error), errors },
        null,
        2,
      ),
    );
    await page.screenshot({
      path: path.join(root, "reports", "browser-failure.png"),
      fullPage: true,
    });
    throw error;
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
