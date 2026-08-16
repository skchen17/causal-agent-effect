const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');
(async () => {
  const [file, out] = process.argv.slice(2);
  const svg = fs.readFileSync(file, 'utf8');
  const vb = svg.match(/viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"/);
  const w = vb ? parseFloat(vb[3]) : 600;
  const h = vb ? parseFloat(vb[4]) : 200;
  const browser = await puppeteer.launch({executablePath: '/usr/bin/google-chrome', headless: 'new', args: ['--no-sandbox']});
  const page = await browser.newPage();
  await page.setViewport({width: Math.ceil(w), height: Math.ceil(h), deviceScaleFactor: 1});
  await page.goto('file://' + file, {waitUntil: 'networkidle0'});
  await page.pdf({path: out, printBackground: true, width: `${w}px`, height: `${h}px`, margin: {top: '0', right: '0', bottom: '0', left: '0'}, pageRanges: '1'});
  await browser.close();
})();
