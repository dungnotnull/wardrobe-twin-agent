/**
 * Content script — runs on supported e-commerce product pages.
 * Extracts product images, title, brand, price, and size chart data
 * from the DOM and makes it available to the popup/background.
 */

// Site-specific extraction strategies
const SITE_CONFIGS = {
  shopee: {
    name: 'Shopee',
    imageSelector: 'div._2a1OPt img, div[data-sqe="img"] img, picture img',
    titleSelector: 'div._1kR56k, span._2v8J5W, div.product-briefing .flex-column span',
    brandSelector: 'a._2H4s8S, div._3b2IG_ a',
    priceSelector: 'div._3e_UQt span, div.product-briefing .flex-column span._2J-y0D',
    sizeChartSelector: 'div.shopee-product-sizing table, table.size-chart-table',
  },
  lazada: {
    name: 'Lazada',
    imageSelector: 'div.gallery-preview-panel img, img[promotion-img], div[class*="gallery"] img',
    titleSelector: 'h1[class*="title"], span[class*="product-title"]',
    brandSelector: 'a[class*="brand"], span[class*="brand-name"]',
    priceSelector: 'span[class*="price"], div[class*="price"] span',
    sizeChartSelector: 'div[class*="size-chart"] table, table[class*="size"]',
  },
  zara: {
    name: 'Zara',
    imageSelector: 'div.product-media img, picture img, .media-image img',
    titleSelector: 'h1.product-name, h1',
    brandSelector: 'h2.brand, a[href*="brand"]',
    priceSelector: 'span.price, div.price span',
    sizeChartSelector: 'div.size-chart table, table.size-chart',
  },
  hm: {
    name: 'H&M',
    imageSelector: 'div.product-detail img, picture img, .image-container img',
    titleSelector: 'h1.heading, h1.product-title',
    brandSelector: 'h2.brand, .brand-name',
    priceSelector: 'span.price, .product-price span',
    sizeChartSelector: 'div.size-guide table, table.size-guide',
  },
  asos: {
    name: 'ASOS',
    imageSelector: 'div.fullSizeImage img, .product-images img, picture img',
    titleSelector: 'h1.product-title, h1',
    brandSelector: 'a.brand, span.brand-name',
    priceSelector: 'span.current-price, div.product-price span',
    sizeChartSelector: 'div.size-guide table, table.size-guide',
  },
};

function detectSite() {
  const hostname = window.location.hostname.toLowerCase();
  for (const [key, config] of Object.entries(SITE_CONFIGS)) {
    if (hostname.includes(key)) return { key, ...config };
  }
  return null;
}

function extractProductData() {
  const site = detectSite();
  if (!site) return { detected: false };

  const images = extractImages(site);
  const title = extractText(site.titleSelector);
  const brand = extractText(site.brandSelector);
  const price = extractText(site.priceSelector);
  const sizeChart = extractSizeChartHTML(site);

  return {
    detected: true,
    url: window.location.href,
    source_site: site.name,
    title,
    brand,
    price,
    images,
    size_chart_html: sizeChart,
  };
}

function extractImages(site) {
  const imgs = document.querySelectorAll(site.imageSelector);
  const urls = new Set();
  imgs.forEach((img) => {
    const src = img.src || img.dataset.src || img.dataset.original;
    if (src && !src.includes('data:') && !src.includes('placeholder')) {
      urls.add(src.startsWith('//') ? 'https:' + src : src);
    }
  });
  return Array.from(urls).slice(0, 5);
}

function extractText(selector) {
  if (!selector) return null;
  const el = document.querySelector(selector);
  return el ? el.textContent.trim() : null;
}

function extractSizeChartHTML(site) {
  if (!site.sizeChartSelector) return null;
  const table = document.querySelector(site.sizeChartSelector);
  return table ? table.outerHTML : null;
}

// Listen for messages from popup/background
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'extract_product') {
    const data = extractProductData();
    sendResponse(data);
    return true;
  }
});

// Notify background when a product page is detected
const site = detectSite();
if (site) {
  chrome.runtime.sendMessage({
    type: 'product_page_detected',
    url: window.location.href,
    site: site.name,
  }).catch(() => {});
}
