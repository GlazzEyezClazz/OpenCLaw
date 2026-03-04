const { chromium } = require('rebrowser-playwright');
(async()=>{
 const url='https://www.wildberries.ru/catalog/226518722/detail.aspx';
 const browser = await chromium.launch({ headless:true, channel:'chrome', args:['--no-sandbox']});
 const context = await browser.newContext();
 await context.addInitScript(() => { delete Object.getPrototypeOf(navigator).webdriver; });
 const page = await context.newPage();
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:90000});
 await page.waitForTimeout(7000);
 const title=await page.title();
 const txt=await page.locator('body').innerText();
 const rub=(txt.match(/\d[\d\s]{2,}\s?₽/g)||[]).slice(0,20);
 console.log('TITLE:',title);console.log('URL:',page.url());console.log('RUB:',rub);
 console.log('SNIP:',txt.slice(0,1000).replace(/\n/g,' | '));
 await browser.close();
})();
