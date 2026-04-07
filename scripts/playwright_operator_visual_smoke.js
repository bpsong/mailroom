const { chromium } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:8000';
const USERNAME = process.env.OPERATOR_USERNAME || 'playwright_user';
const PASSWORD = process.env.OPERATOR_PASSWORD || 'Password!1234';
const RECIPIENT_SEARCH = process.env.OPERATOR_RECIPIENT_SEARCH || 'Test Recipient';
const TARGET_STATUS = process.env.OPERATOR_TARGET_STATUS || 'awaiting_pickup';
const HEADLESS = (process.env.PLAYWRIGHT_HEADLESS || 'false').toLowerCase() !== 'false';

const STATUS_LABELS = {
    awaiting_pickup: 'Awaiting Pickup',
    out_for_delivery: 'Out for Delivery',
    delivered: 'Delivered',
    returned: 'Returned',
};

function escapeRegex(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function timestampId() {
    return new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14);
}

async function screenshot(page, name) {
    await page.screenshot({
        path: `test-results/${timestampId()}-${name}.png`,
        fullPage: true,
    });
}

async function gotoStable(page, url) {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('load', { timeout: 15000 }).catch(() => { });
}

async function login(page) {
    await gotoStable(page, `${BASE_URL}/auth/login`);
    await page.locator('#username').waitFor({ state: 'visible', timeout: 15000 });
    await page.fill('#username', USERNAME);
    await page.fill('#password', PASSWORD);
    await screenshot(page, 'operator-login');

    await Promise.all([
        page.waitForURL('**/dashboard', { timeout: 15000 }),
        page.locator('button[type="submit"]').click(),
    ]);

    await page.locator('text=Dashboard').first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => { });
    await screenshot(page, 'operator-dashboard');
}

async function registerPackage(page, trackingNo) {
    await gotoStable(page, `${BASE_URL}/packages/new`);
    await page.locator('#register-package-form').waitFor({ state: 'visible', timeout: 15000 });
    await page.fill('input[name="tracking_no"]', trackingNo);
    await page.fill('input[name="carrier"]', 'Playwright Express');
    const recipientSearch = page.locator('#recipient-search');
    const results = page.locator('#recipient-results [data-recipient-id]');

    if (RECIPIENT_SEARCH.trim()) {
        await recipientSearch.fill(RECIPIENT_SEARCH);
        await page.waitForTimeout(800);
    }

    if ((await results.count()) === 0) {
        await recipientSearch.fill('');
        await recipientSearch.press('A');
        await recipientSearch.press('Backspace');
        await page.waitForTimeout(800);
    }

    const matchedRecipient = RECIPIENT_SEARCH.trim()
        ? results.filter({ hasText: new RegExp(escapeRegex(RECIPIENT_SEARCH), 'i') }).first()
        : results.first();
    const fallbackRecipient = results.first();
    const recipientToUse = (await matchedRecipient.count()) > 0 ? matchedRecipient : fallbackRecipient;

    await recipientToUse.waitFor({ state: 'visible', timeout: 15000 });
    const recipientText = (await recipientToUse.innerText()).trim().replace(/\s+/g, ' ');
    await recipientToUse.click();

    await page.fill('textarea[name="notes"]', `Operator visual smoke package ${trackingNo}`);
    await screenshot(page, 'operator-register-form');

    await Promise.all([
        page.waitForURL('**/packages', { timeout: 15000 }),
        page.locator('#submit-btn').click(),
    ]);

    await page.locator('#package-list').waitFor({ state: 'visible', timeout: 15000 });
    await screenshot(page, 'operator-packages-list-after-register');

    return recipientText;
}

async function openPackageDetail(page, trackingNo) {
    await page.fill('input[name="query"]', trackingNo);
    await page.keyboard.press('Enter');
    await page.locator('#package-list').waitFor({ state: 'visible', timeout: 15000 });

    const detailLink = page.locator(`a[href^="/packages/"]`).filter({ hasText: 'View' }).first();
    await detailLink.waitFor({ state: 'visible', timeout: 15000 });

    await Promise.all([
        page.waitForURL('**/packages/*', { timeout: 15000 }),
        detailLink.click(),
    ]);

    await page.locator('h2.card-title').first().waitFor({ state: 'visible', timeout: 15000 });
    await screenshot(page, 'operator-package-detail-before-status-update');
}

async function updateStatus(page, trackingNo) {
    const expectedLabel = STATUS_LABELS[TARGET_STATUS];
    if (!expectedLabel) {
        throw new Error(`Unsupported OPERATOR_TARGET_STATUS: ${TARGET_STATUS}`);
    }

    await page.getByRole('button', { name: 'Update Status' }).click();
    const modal = page.locator('#status_modal');
    await modal.waitFor({ state: 'visible', timeout: 10000 });
    await modal.locator('select[name="status"]').selectOption(TARGET_STATUS);
    await modal.locator('textarea[name="notes"]').fill(`Visual smoke status update for ${trackingNo}`);
    await screenshot(page, 'operator-status-modal');

    await modal.getByRole('button', { name: 'Update Status' }).click();
    await page.waitForTimeout(2200);
    await page.locator('h2.card-title').first().waitFor({ state: 'visible', timeout: 15000 });
    await screenshot(page, 'operator-package-detail-after-status-update');

    await page.getByText(expectedLabel, { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
    await page.getByText(`Visual smoke status update for ${trackingNo}`, { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
}

async function main() {
    const browser = await chromium.launch({ headless: HEADLESS });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    const trackingNo = `PW-SMOKE-${Date.now()}`;

    try {
        await login(page);
        const recipientText = await registerPackage(page, trackingNo);
        await openPackageDetail(page, trackingNo);
        await page.getByText(trackingNo, { exact: true }).first().waitFor({ state: 'visible', timeout: 15000 });
        await updateStatus(page, trackingNo);

        console.log(
            `OPERATOR_SMOKE_OK tracking=${trackingNo} recipient="${recipientText}" status=${TARGET_STATUS} url=${page.url()}`
        );
    } finally {
        await browser.close();
    }
}

main().catch((error) => {
    console.error('OPERATOR_SMOKE_FAILED', error);
    process.exit(1);
});
