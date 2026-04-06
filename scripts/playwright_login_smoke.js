const { chromium } = require('@playwright/test');

async function main() {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    try {
        await page.goto('http://127.0.0.1:8000/auth/login', { waitUntil: 'networkidle' });
        await page.fill('#username', 'playwright_user');
        await page.fill('#password', 'Playwright123!');

        await Promise.all([
            page.waitForURL('**/dashboard', { timeout: 15000 }),
            page.click('button[type="submit"]'),
        ]);

        const title = await page.title();
        console.log(`LOGIN_OK title=${title} url=${page.url()}`);
    } finally {
        await browser.close();
    }
}

main().catch((error) => {
    console.error('LOGIN_FAILED', error);
    process.exit(1);
});
