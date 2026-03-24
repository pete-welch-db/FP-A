const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'https://nova-molding-fpa-lite-dev-984752964297111.11.azure.databricksapps.com';
const OUTPUT_DIR = path.join(__dirname, 'screenshots');

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    channel: 'chrome', // Use system Chrome if available
  });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  try {
    // 1. Navigate to settings and take screenshot
    console.log('Navigating to settings...');
    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: path.join(OUTPUT_DIR, '01_settings_initial.png'), fullPage: true });
    console.log('Screenshot 1 saved: 01_settings_initial.png');

    // 2. Click Milacron radio button and wait for reload (Streamlit radio)
    console.log('Clicking Milacron radio button...');
    const milacronOption = page.locator('label').filter({ hasText: 'Milacron' }).first();
    await milacronOption.click({ timeout: 5000 });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000); // Extra wait for any reload
    await page.screenshot({ path: path.join(OUTPUT_DIR, '02_settings_milacron.png'), fullPage: true });
    console.log('Screenshot 2 saved: 02_settings_milacron.png');

    // 3. Navigate to revenue-deep-dive
    console.log('Navigating to revenue-deep-dive...');
    await page.goto(`${BASE_URL}/revenue-deep-dive`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // Wait for data to load
    await page.screenshot({ path: path.join(OUTPUT_DIR, '03_revenue_deep_dive.png'), fullPage: true });
    console.log('Screenshot 3 saved: 03_revenue_deep_dive.png');

    // 4. Navigate to executive-summary
    console.log('Navigating to executive-summary...');
    await page.goto(`${BASE_URL}/executive-summary`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000); // Wait for dashboard to load
    await page.screenshot({ path: path.join(OUTPUT_DIR, '04_executive_summary.png'), fullPage: true });
    console.log('Screenshot 4 saved: 04_executive_summary.png');

  } catch (err) {
    console.error('Error:', err.message);
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'error.png'), fullPage: true });
    throw err;
  } finally {
    await browser.close();
  }

  console.log('All screenshots saved to', OUTPUT_DIR);
}

main();
