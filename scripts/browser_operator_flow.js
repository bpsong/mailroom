const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

async function main() {
    const outDir = path.join(__dirname, '..', 'output', 'playwright');
    fs.mkdirSync(outDir, { recursive: true });
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const trackingNo = 'OP-TEST-' + Date.now().toString().slice(-8);

    try {
        // 1. Login as operator
        await page.goto('http://127.0.0.1:8000/auth/login', { waitUntil: 'networkidle' });
        await page.fill('#username', 'playwright_user');
        await page.fill('#password', 'Password!1234');
        await Promise.all([
            page.waitForURL('**/dashboard', { timeout: 15000 }),
            page.click('button[type="submit"]'),
        ]);
        console.log('LOGIN_OK url=' + page.url());
        await page.screenshot({ path: path.join(outDir, 'operator-1-dashboard.png') });

        // 2. Go to register form
        await page.goto('http://127.0.0.1:8000/packages/new', { waitUntil: 'networkidle' });
        const carrierOptions = await page.$$eval('select[name="carrier"] option', els => els.map(e => ({ value: e.value, text: e.textContent.trim() })));
        console.log('CARRIERS=' + JSON.stringify(carrierOptions));
        if (carrierOptions.length < 2) throw new Error('No carriers available');
        const carrierName = carrierOptions[1].value || carrierOptions[1].text;
        await page.fill('input[name="tracking_no"]', trackingNo);
        await page.selectOption('select[name="carrier"]', { index: 1 });
        await page.fill('textarea[name="notes"]', 'Browser E2E by operator');
        await page.screenshot({ path: path.join(outDir, 'operator-2-register-form.png') });

        // 3. Select recipient via autocomplete (Sarah Johnson EMP002)
        await page.click('#recipient-search');
        await page.type('#recipient-search', 'Sarah', { delay: 60 });
        try {
            await page.waitForSelector('#recipient-results [data-recipient-id]', { timeout: 10000 });
        } catch (e) {
            const html = await page.$eval('#recipient-results', el => el.innerHTML.slice(0, 500)).catch(() => 'NO_RESULTS_DIV');
            console.log('RECIPIENT_RESULTS_HTML=' + html);
            // Fallback: query JSON API directly and set hidden field
            const api = await page.evaluate(async () => {
                const r = await fetch('/recipients/search?q=Sarah&limit=5', { headers: { 'Accept': 'application/json' } });
                const t = await r.text();
                return t.slice(0, 1000);
            });
            console.log('RECIPIENT_API=' + api);
            throw e;
        }
        const recInfo = await page.$eval('#recipient-results [data-recipient-id]', el => ({
            id: el.getAttribute('data-recipient-id'),
            name: el.getAttribute('data-recipient-name'),
            email: el.getAttribute('data-recipient-email'),
        }));
        console.log('RECIPIENT=' + JSON.stringify(recInfo));
        await page.click('#recipient-results [data-recipient-id]');
        await page.waitForFunction(() => document.getElementById('recipient-id').value.length > 5, null, { timeout: 5000 });
        const recipientId = await page.$eval('#recipient-id', el => el.value);
        console.log('RECIPIENT_ID=' + recipientId);
        await page.screenshot({ path: path.join(outDir, 'operator-3-recipient-selected.png') });

        // 4. Submit package
        await Promise.all([
            page.waitForURL('**/packages', { timeout: 15000 }),
            page.click('#submit-btn'),
        ]);
        console.log('REGISTER_SUBMIT_OK url=' + page.url() + ' tracking=' + trackingNo);

        // 5. Find package in list via search query
        await page.goto('http://127.0.0.1:8000/packages?query=' + encodeURIComponent(trackingNo), { waitUntil: 'networkidle' });
        await page.screenshot({ path: path.join(outDir, 'operator-4-package-list.png') });
        const detailHref = await page.evaluate((tracking) => {
            const links = Array.from(document.querySelectorAll('a[href^="/packages/"]'));
            const uuidRe = /^\/packages\/[0-9a-fA-F-]{36}$/;
            const uuidLinks = links.map(a => a.getAttribute('href')).filter(h => uuidRe.test(h || ''));
            if (uuidLinks.length > 0) return uuidLinks[0];
            // fallback: row containing tracking number
            const bodyText = document.body.innerText || '';
            if (bodyText.includes(tracking)) {
                const row = Array.from(document.querySelectorAll('tr')).find(tr => (tr.innerText || '').includes(tracking));
                if (row) {
                    const a = row.querySelector('a[href^="/packages/"]');
                    if (a) return a.getAttribute('href');
                }
            }
            return null;
        }, trackingNo);
        console.log('DETAIL_LINK=' + detailHref);
        if (!detailHref) throw new Error('New package link not found in list');
        const packageId = detailHref.split('/')[2];

        // 6. Open detail, complete delivery
        await page.goto('http://127.0.0.1:8000' + detailHref, { waitUntil: 'networkidle' });
        await page.screenshot({ path: path.join(outDir, 'operator-5-detail-before.png') });
        await page.click('text=Update Status');
        await page.waitForSelector('#status_modal select[name="status"]', { timeout: 5000, state: 'visible' });
        await page.selectOption('#status_modal select[name="status"]', 'delivered');
        await page.fill('#status_modal textarea[name="notes"]', 'Delivered to recipient - E2E');
        await page.screenshot({ path: path.join(outDir, 'operator-6-status-modal.png') });
        await page.click('#status_modal button[type="submit"]');
        await page.waitForSelector('text=Delivered', { timeout: 10000 });
        await page.waitForTimeout(1500);
        await page.goto('http://127.0.0.1:8000' + detailHref, { waitUntil: 'networkidle' });
        await page.screenshot({ path: path.join(outDir, 'operator-7-delivered.png') });
        const badgeText = await page.textContent('#package-status-badge').catch(() => '');
        const timelineText = await page.textContent('#package-timeline').catch(() => '');
        console.log('DELIVERY_OK package=' + packageId + ' tracking=' + trackingNo + ' badge=' + (badgeText || '').trim() + ' timeline_has_delivered=' + (timelineText || '').includes('Delivered'));
    } finally {
        await browser.close();
    }
}

main().catch((e) => { console.error('FLOW_FAILED', e); process.exit(1); });
