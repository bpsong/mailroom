const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

async function checkPage(page, name, outDir, expectText) {
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const status = await page.evaluate(() => document.title + ' ||| ' + (document.body ? document.body.innerText.slice(0, 200) : ''));
    const has500 = /internal server error|traceback|500/i.test(status) && !/csrf/i.test(status);
    const hasExpected = expectText ? (await page.getByText(expectText, { exact: false }).count().catch(() => 0)) > 0 : true;
    await page.screenshot({ path: path.join(outDir, name + '.png') });
    console.log(`PAGE name=${name} title=${status.split(' ||| ')[0]} has500=${has500} expect[${expectText}]=${hasExpected}`);
    if (has500) throw new Error('500-style error on ' + name);
    if (!hasExpected) throw new Error(`Expected text "${expectText}" not found on ${name}`);
}

async function main() {
    const outDir = path.join(__dirname, '..', 'output', 'playwright');
    fs.mkdirSync(outDir, { recursive: true });
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));
    page.on('response', (r) => { if (r.status() >= 500) errors.push(`HTTP${r.status()}: ${r.url()}`); });

    try {
        // 1. Login as admin
        await page.goto('http://127.0.0.1:8000/auth/login', { waitUntil: 'networkidle' });
        await page.fill('#username', 'normal_admin');
        await page.fill('#password', 'Password!1234');
        await Promise.all([
            page.waitForURL('**/dashboard', { timeout: 15000 }),
            page.click('button[type="submit"]'),
        ]);
        console.log('ADMIN_LOGIN_OK url=' + page.url());
        await page.screenshot({ path: path.join(outDir, 'admin-1-dashboard.png') });

        // 2. Users list (guide: Users -> review list)
        await page.goto('http://127.0.0.1:8000/admin/users', { waitUntil: 'domcontentloaded' });
        await checkPage(page, 'admin-2-users', outDir, 'playwright_user');

        // 3. Recipients list (guide: Recipients -> review list)
        await page.goto('http://127.0.0.1:8000/admin/recipients', { waitUntil: 'domcontentloaded' });
        await checkPage(page, 'admin-3-recipients', outDir, 'Recipient Management');

        // 4. CSV import dry-run: upload + validate only, NEVER confirm (no DB change)
        await page.goto('http://127.0.0.1:8000/admin/recipients/import', { waitUntil: 'domcontentloaded' });
        await checkPage(page, 'admin-4-import-page', outDir, 'CSV Format Requirements');
        await page.setInputFiles('#csv-file', path.join(__dirname, '..', 'sample_recipients.csv'));
        await page.waitForSelector('#validation-results:not(.hidden)', { timeout: 15000 });
        await page.waitForTimeout(1500);
        await page.screenshot({ path: path.join(outDir, 'admin-5-import-validated.png') });
        const validationText = await page.textContent('#validation-results').catch(() => '');
        console.log('IMPORT_VALIDATE_OK text=' + (validationText || '').replace(/\s+/g, ' ').slice(0, 200));
        const confirmVisible = await page.isVisible('#confirm-import-btn');
        console.log('IMPORT_CONFIRM_SHOWN=' + confirmVisible + ' (not clicked — dry run only)');

        // 5. Reports (guide: Reports -> apply filters -> review)
        await page.goto('http://127.0.0.1:8000/admin/reports', { waitUntil: 'domcontentloaded' });
        await checkPage(page, 'admin-6-reports', outDir, 'Reports');

        // 6. Super-admin-only page must be denied for admin (RBAC negative check)
        await page.goto('http://127.0.0.1:8000/admin/settings', { waitUntil: 'domcontentloaded' });
        const settingsBody = await page.textContent('body').catch(() => '');
        const denied = /403|forbidden|access denied/i.test(settingsBody || '');
        await page.screenshot({ path: path.join(outDir, 'admin-7-settings-denied.png') });
        console.log('SETTINGS_DENIED_FOR_ADMIN=' + denied);
        if (!denied) throw new Error('Expected 403 on /admin/settings for admin role');

        // 7. Operator must be denied admin pages (RBAC negative check)
        const opCtx = await browser.newContext();
        const op = await opCtx.newPage();
        await op.goto('http://127.0.0.1:8000/auth/login', { waitUntil: 'networkidle' });
        await op.fill('#username', 'playwright_user');
        await op.fill('#password', 'Password!1234');
        await Promise.all([
            op.waitForURL('**/dashboard', { timeout: 15000 }),
            op.click('button[type="submit"]'),
        ]);
        await op.goto('http://127.0.0.1:8000/admin/users', { waitUntil: 'domcontentloaded' });
        const opBody = await op.textContent('body').catch(() => '');
        const opDenied = /403|forbidden|access denied/i.test(opBody || '');
        await op.screenshot({ path: path.join(outDir, 'operator-8-admin-denied.png') });
        console.log('ADMIN_DENIED_FOR_OPERATOR=' + opDenied);
        if (!opDenied) throw new Error('Expected 403 on /admin/users for operator role');
        await opCtx.close();

        const realErrors = errors.filter((e) => !/favicon/i.test(e));
        console.log('CONSOLE_OR_5XX_ERRORS=' + realErrors.length);
        realErrors.slice(0, 10).forEach((e) => console.log('  ' + e));
        if (realErrors.length > 0) throw new Error(realErrors.length + ' page/5xx errors');
        console.log('ADMIN_VISUAL_OK');
    } finally {
        await browser.close();
    }
}

main().catch((e) => { console.error('ADMIN_FLOW_FAILED', e); process.exit(1); });
