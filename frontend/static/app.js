const API_BASE = window.MEDI_API_BASE || "/api";
const root = document.getElementById("app");

const icon = (name) => {
  const paths = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="m15 18-6-6 6-6"/><path d="M9 12h11"/>',
    pill: '<path d="m10.5 20.5 10-10a5.66 5.66 0 0 0-8-8l-10 10a5.66 5.66 0 0 0 8 8Z"/><path d="m8.5 8.5 7 7"/>',
    flask: '<path d="M9 3h6m-5 0v7l-5.5 8.5A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-2.5L14 10V3"/><path d="M8 16h8"/>',
    pin: '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
    phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2A19.8 19.8 0 0 1 3.1 5.2 2 2 0 0 1 5.1 3h3a2 2 0 0 1 2 1.7l.4 2.8a2 2 0 0 1-.6 1.7L8 11a16 16 0 0 0 5 5l1.8-1.9a2 2 0 0 1 1.7-.6l2.8.4a2 2 0 0 1 1.7 2Z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    map: '<path d="M3 6 9 3l6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15m6-12v15"/>',
    trend: '<path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/>',
    trash: '<path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v7m6-7v7"/>',
    basket: '<path d="m5 9 3-6m11 6-3-6M3 9h18l-2 11H5L3 9Z"/><path d="M9 13v3m6-3v3"/>',
    heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/>',
    cross: '<path d="M10 3H7a4 4 0 0 0-4 4v3h7V3Zm4 0h3a4 4 0 0 1 4 4v3h-7V3ZM3 14v3a4 4 0 0 0 4 4h3v-7H3Zm11 0h7v3a4 4 0 0 1-4 4h-3v-7Z"/>',
    arrowUp: '<path d="M12 19V5m-7 7 7-7 7 7"/>',
    close: '<path d="m18 6-12 12M6 6l12 12"/>',
    spark: '<path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3Z"/>',
    shield: '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.spark}</svg>`;
};

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));
const rupees = (value) => value == null ? "—" : new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR", maximumFractionDigits: 2,
}).format(Number(value));
const dateLabel = (value) => value ? new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "date unavailable";

function readCart() {
  try { return JSON.parse(localStorage.getItem("sehatsetu-cart")) || { medicines: [], tests: [] }; }
  catch { return { medicines: [], tests: [] }; }
}

const state = {
  page: "home",
  searchMode: "medicines",
  query: "",
  search: { status: "idle", results: [], error: "" },
  medicine: { id: null, status: "idle", detail: null, prices: [], error: "" },
  test: { id: null, status: "idle", item: null, prices: [], error: "", nablOnly: false, homeOnly: false },
  cart: readCart(),
  useAlternatives: false,
  estimate: { status: "idle", result: null, error: "" },
  toast: "",
  requestVersion: 0,
};

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let body;
  try { body = await response.json(); } catch { body = null; }
  if (!response.ok) {
    const message = body?.detail || body?.error || `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return body;
}

function toast(message) {
  state.toast = message;
  render();
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => { state.toast = ""; render(); }, 2300);
}

function saveCart() {
  localStorage.setItem("sehatsetu-cart", JSON.stringify(state.cart));
}

function cartCount() {
  return state.cart.medicines.length + state.cart.tests.length;
}

function header() {
  return `<header class="topbar"><div class="topbar-inner">
    <a href="#home" class="brand" data-action="home" aria-label="SehatSetu home">
      <span class="brand-mark">${icon("cross")}</span><span>sehat<em>setu</em></span>
    </a>
    <nav class="nav" aria-label="Main navigation">
      <button class="nav-button home-nav ${state.page === "home" ? "active" : ""}" data-action="home">Explore</button>
      <button class="nav-button nav-estimate ${state.page === "estimate" ? "active" : ""}" data-action="estimate">${icon("basket")} Estimate <span class="cart-count">${cartCount()}</span></button>
    </nav>
  </div></header>`;
}

function mobileNav() {
  return `<nav class="mobile-bottom" aria-label="Quick navigation">
    <button class="mobile-nav-button ${state.page === "home" ? "active" : ""}" data-action="home">${icon("search")}Explore</button>
    <button class="mobile-nav-button ${state.page === "estimate" ? "active" : ""}" data-action="estimate">${icon("basket")}Estimate ${cartCount() ? `(${cartCount()})` : ""}</button>
  </nav>`;
}

function footer() {
  return `<footer class="footer"><span><strong>SehatSetu</strong> · Compare with confidence</span><span>Prices may change. Confirm availability before visiting.</span></footer>`;
}

function safetyNotice() {
  return `<div class="safety-notice">${icon("shield")}<span><strong>Sample directory and lab prices.</strong> Medicine prices are catalogue MRP references, not pharmacy quotes or live stock. Verify current prices and availability directly with providers; confirm any medicine change with your prescriber or pharmacist.</span></div>`;
}

function stateBox(kind, title, message, action = "") {
  const iconName = kind === "error" ? "close" : kind === "loading" ? "" : "spark";
  if (kind === "loading") return `<div class="loading-state"><div class="spinner"></div><h3>${esc(title)}</h3><p>${esc(message)}</p></div>`;
  return `<div class="${kind}-state"><div class="state-icon">${icon(iconName)}</div><h3>${esc(title)}</h3><p>${esc(message)}</p>${action}</div>`;
}

function searchBox() {
  const terms = state.searchMode === "medicines"
    ? ["Dolo 650", "Crocin", "paracetamol"]
    : ["CBC", "HbA1c", "thyroid profile"];
  return `<div class="search-card">
    <div class="search-tabs" role="tablist" aria-label="Search type">
      <button class="search-tab ${state.searchMode === "medicines" ? "active" : ""}" data-action="search-mode" data-mode="medicines" role="tab" aria-selected="${state.searchMode === "medicines"}">Medicines</button>
      <button class="search-tab ${state.searchMode === "tests" ? "active" : ""}" data-action="search-mode" data-mode="tests" role="tab" aria-selected="${state.searchMode === "tests"}">Tests</button>
    </div>
    <div class="search-row">${icon("search")}
      <input id="home-search" class="search-input" type="search" autocomplete="off" placeholder="${state.searchMode === "medicines" ? "Search a medicine or ingredient" : "Search a diagnostic test"}" value="${esc(state.query)}" aria-label="Search ${state.searchMode}" />
      ${state.query ? `<button class="button-quiet" data-action="clear-search" aria-label="Clear search">${icon("close")}</button>` : ""}
      <button class="search-go" data-action="submit-search" aria-label="Search">${icon("arrow")}</button>
    </div>
  </div>
  <div class="example-row"><span>Try:</span>${terms.map((term) => `<button class="chip" data-action="search-chip" data-query="${esc(term)}">${esc(term)}</button>`).join("")}</div>`;
}

function homeResults() {
  if (!state.query.trim()) return "";
  if (state.search.status === "loading") return `<section class="result-list">${stateBox("loading", "Searching…", "Looking across medicines and tests.")}</section>`;
  if (state.search.status === "error") return `<section class="result-list">${stateBox("error", "Search couldn’t load", state.search.error, '<button class="button-secondary" data-action="retry-search">Try again</button>')}</section>`;
  if (state.search.status === "empty") return `<section class="result-list">${stateBox("empty", "No matches yet", `We couldn't find ${state.searchMode === "medicines" ? "a medicine" : "a test"} for “${state.query}”. Try another name or ingredient.`)}</section>`;
  if (state.search.status !== "success") return "";
  return `<section class="result-list">${state.search.results.map((item) => state.searchMode === "medicines"
    ? `<article class="result-card"><span class="result-icon">${icon("pill")}</span><div class="result-main"><strong>${esc(item.name)}</strong><small>${esc(item.manufacturer || "Manufacturer unavailable")} · ${esc(item.form || "Medicine")}${item.salt_key ? ` · ${esc(item.salt_key)}` : ""}</small></div><div class="result-price"><strong>${rupees(item.mrp)}</strong><small>MRP</small></div><button class="button-secondary button-small" data-action="open-medicine" data-id="${item.id}">Compare</button></article>`
    : `<article class="result-card"><span class="result-icon">${icon("flask")}</span><div class="result-main"><strong>${esc(item.name)}</strong><small>${esc(item.category || "Diagnostic test")}${item.fasting_required ? " · Confirm fasting instructions with lab" : ""}</small></div><button class="button-secondary button-small" data-action="open-test" data-id="${item.id}">Compare labs</button></article>`
  ).join("")}</section>`;
}

function homePage() {
  return `<div class="home-hero">
    <section class="hero-panel">
      <div class="eyebrow">Smarter care starts here</div>
      <div class="hero-art">${icon("heart")}</div>
      <h1>Good care.<br /><span>Clearer costs.</span></h1>
      <p class="hero-copy">Compare medicine and diagnostic test prices around Nagpur, all in one simple place.</p>
      ${searchBox()}
    </section>
    <aside class="hero-aside">
      <div class="aside-orbit"><span class="orbit-center">${icon("shield")}</span><span class="orbit-dot one">${icon("pill")}</span><span class="orbit-dot two">${icon("flask")}</span></div>
      <div class="aside-bottom"><div class="eyebrow">Your care, considered</div><h3>Find the right fit for your budget.</h3><p>See nearby options, compare what matters, and build a simple estimate before you go.</p></div>
    </aside>
  </div>
  ${homeResults()}
  <section>
    <div class="section-heading"><div><div class="eyebrow">Get started</div><h2>Popular searches</h2></div><button class="text-link" data-action="clear-search">Explore all</button></div>
    <div class="popular-grid">
      <button class="popular-card" data-action="popular" data-mode="medicines" data-query="Dolo 650"><span class="popular-icon">${icon("pill")}</span><strong>Dolo 650</strong><small>Medicine comparison</small></button>
      <button class="popular-card" data-action="popular" data-mode="medicines" data-query="paracetamol"><span class="popular-icon">${icon("spark")}</span><strong>Paracetamol</strong><small>Search by ingredient</small></button>
      <button class="popular-card" data-action="popular" data-mode="tests" data-query="CBC"><span class="popular-icon">${icon("flask")}</span><strong>Complete blood count</strong><small>Lab price comparison</small></button>
      <button class="popular-card" data-action="popular" data-mode="tests" data-query="HbA1c"><span class="popular-icon">${icon("trend")}</span><strong>HbA1c</strong><small>Lab price comparison</small></button>
    </div>
  </section>`;
}

function backHeader(title, subtitle = "") {
  return `<div class="page-header"><button class="back-button" data-action="home" aria-label="Back to search">${icon("back")}</button><div><h1>${esc(title)}</h1>${subtitle ? `<p>${esc(subtitle)}</p>` : ""}</div></div>`;
}

function alternativeSaving(alt) {
  const saving = alt.reference_savings_vs_selected_mrp;
  if (saving?.amount == null) {
    return `<span class="tag">Pack sizes cannot be compared</span>`;
  }
  const amount = Number(saving.amount);
  if (amount > 0) return `<span class="saving-badge">${icon("trend")} Lower reference by ${rupees(amount)} (${esc(saving.percent)}%)</span>`;
  if (amount < 0) return `<span class="tag">Reference is ${rupees(Math.abs(amount))} higher</span>`;
  return `<span class="tag">Same reference price</span>`;
}

function mapsUrl(place) {
  const query = `${place.lat || ""},${place.lng || ""}`;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function placeMeta(place, showPhone = true) {
  return `<div class="place-meta"><span>${icon("pin")}${esc(place.address || place.area || "Address unavailable")}</span>${showPhone && place.phone ? `<span><a href="tel:${esc(place.phone)}" class="map-link">${icon("phone")}${esc(place.phone)}</a></span>` : ""}<span>${icon("clock")}${esc(place.hours || "Hours unavailable")}</span><span><a class="map-link" href="${mapsUrl(place)}" target="_blank" rel="noopener">${icon("map")}Open in Maps</a></span></div>`;
}

function medicinePage() {
  if (state.medicine.status === "loading") return `${backHeader("Medicine comparison", "Loading reference prices and pharmacy quotes")} ${stateBox("loading", "Finding price information", "Gathering catalogue references and pharmacy listings.")}`;
  if (state.medicine.status === "error") return `${backHeader("Medicine comparison")} ${stateBox("error", "Medicine details couldn’t load", state.medicine.error, '<button class="button-secondary" data-action="retry-medicine">Try again</button>')}`;
  const detail = state.medicine.detail;
  if (!detail) return `${backHeader("Medicine comparison")} ${stateBox("empty", "Medicine unavailable", "Try searching for another medicine.")}`;
  const med = detail.medicine;
  const alternatives = detail.alternatives || [];
  const prices = state.medicine.prices || [];
  return `${backHeader("Medicine comparison", "Compare catalogue reference prices and pharmacy quotes")}
    <section class="medicine-overview"><div><div class="eyebrow">${esc(med.form || "Medicine")}${med.form_variant ? ` · ${esc(med.form_variant.toUpperCase())}` : ""}</div><h1>${esc(med.name)}</h1><p>${esc(med.manufacturer)}${med.salt_key ? ` · ${esc(med.salt_key)}` : ""}</p></div><div class="medicine-main-price"><strong>${rupees(med.mrp)}</strong><span>Catalogue MRP reference</span><div style="margin-top:11px"><button class="button-primary" data-action="add-medicine" data-id="${med.id}">${icon("plus")} Add to estimate</button></div></div></section>
    <div class="detail-grid">
      <section class="panel"><div class="section-title"><div><h2>Equivalent medicine references</h2><p>Same listed ingredients, form and release type. Reference prices are normalized to this pack size; confirm strength and pack before choosing.</p></div><span class="count-pill">${alternatives.length} options</span></div>
        ${alternatives.length ? `<div class="table-wrap"><table><thead><tr><th>Medicine</th><th>Catalogue MRP</th><th>Price / unit</th><th>Reference for this pack</th><th>Reference difference</th><th></th></tr></thead><tbody>${alternatives.map((alt) => `<tr><td><div class="product-cell"><strong>${esc(alt.name)}</strong><small>${esc(alt.manufacturer || "")}</small></div></td><td class="price-main">${rupees(alt.mrp)}</td><td>${rupees(alt.price_per_unit)}</td><td class="price-main">${rupees(alt.reference_price_for_selected_pack)}</td><td>${alternativeSaving(alt)}</td><td><button class="button-secondary button-small" data-action="add-medicine" data-id="${alt.id}">${icon("plus")} Add</button></td></tr>`).join("")}</tbody></table></div>` : stateBox("empty", "No alternatives found", "There are no matching medicines with the same ingredient and form yet.")}
      </section>
      <section class="panel"><div class="section-title"><div><h2>Pharmacy quotes</h2><p>Verified store prices and availability, sorted lowest first</p></div><span class="count-pill">${prices.length} nearby</span></div>
        ${prices.length ? `<div class="table-wrap"><table><thead><tr><th>Pharmacy</th><th>Area</th><th>Price</th><th>Availability</th></tr></thead><tbody>${prices.map((item) => `<tr><td><div class="product-cell"><strong>${esc(item.pharmacy.name)}</strong><small>${esc(item.pharmacy.address)}</small><a class="map-link" href="${mapsUrl(item.pharmacy)}" target="_blank" rel="noopener">${icon("map")} Open in Maps</a></div></td><td>${esc(item.pharmacy.area)}</td><td class="price-main">${rupees(item.price)}<small class="place-sub">Updated ${dateLabel(item.last_updated)}</small></td><td><span class="tag ${item.in_stock ? "tag-accredited" : ""}">${item.in_stock ? "In stock" : "Out of stock"}</span></td></tr>`).join("")}</tbody></table></div><div class="pharmacy-list" style="margin-top:14px">${prices.map((item) => `<article class="price-card"><div><div class="place-header"><span class="place-icon">${icon("cross")}</span><div><strong class="place-name">${esc(item.pharmacy.name)}</strong><span class="place-sub">${esc(item.pharmacy.type.replaceAll("_", " "))} · ${esc(item.pharmacy.area)}</span></div></div>${placeMeta(item.pharmacy)}<div class="test-info"><span class="tag ${item.in_stock ? "tag-accredited" : ""}">${item.in_stock ? "In stock" : "Out of stock"}</span></div></div><div class="place-price"><strong>${rupees(item.price)}</strong><small>per pack · updated ${dateLabel(item.last_updated)}</small></div></article>`).join("")}</div>` : stateBox("empty", "No verified pharmacy quotes yet", "Catalogue MRPs are shown above. Store specific prices and stock will appear here when verified listings are available.")}
      </section>
    </div>`;
}

function testPage() {
  if (state.test.status === "loading") return `${backHeader("Test comparison", "Loading lab prices")} ${stateBox("loading", "Finding lab prices", "Gathering diagnostic test listings.")}`;
  if (state.test.status === "error") return `${backHeader("Test comparison")} ${stateBox("error", "Test prices couldn’t load", state.test.error, '<button class="button-secondary" data-action="retry-test">Try again</button>')}`;
  const item = state.test.item;
  if (!item) return `${backHeader("Test comparison")} ${stateBox("empty", "Test unavailable", "Try searching for another diagnostic test.")}`;
  const filtered = state.test.prices.filter((row) => (!state.test.nablOnly || row.lab.nabl_accredited) && (!state.test.homeOnly || row.lab.home_collection));
  return `${backHeader("Lab comparison", "Compare prices and collection options")}
    <section class="medicine-overview"><div><div class="eyebrow">${esc(item.category || "Diagnostic test")}</div><h1>${esc(item.name)}</h1><p>${item.fasting_required ? "Fasting may be required; confirm with the lab or clinician" : "Confirm any preparation instructions with the lab"}${item.aliases ? ` · Also known as ${esc(item.aliases.split(";").slice(0,2).join(", "))}` : ""}</p></div><div class="medicine-main-price"><span>Compare local lab rates</span><div style="margin-top:12px"><button class="button-primary" data-action="add-test" data-id="${item.id}">${icon("plus")} Add to estimate</button></div></div></section>
    <section class="panel"><div class="section-title"><div><h2>Prices by lab</h2><p>Lowest price first · Collection fees shown separately</p></div><span class="count-pill">${filtered.length} of ${state.test.prices.length} labs</span></div>
      <div class="filter-row" style="margin-bottom:17px"><label class="filter-control"><input type="checkbox" data-filter="nabl" ${state.test.nablOnly ? "checked" : ""}/> NABL accredited</label><label class="filter-control"><input type="checkbox" data-filter="home" ${state.test.homeOnly ? "checked" : ""}/> Home collection</label></div>
      ${filtered.length ? `<div class="lab-list">${filtered.map((row) => `<article class="price-card"><div><div class="place-header"><span class="place-icon">${icon("flask")}</span><div><strong class="place-name">${esc(row.lab.name)}</strong><span class="place-sub">${esc(row.lab.address)}</span></div></div><div class="test-info"><span class="tag ${row.lab.nabl_accredited ? "tag-accredited" : ""}">${row.lab.nabl_accredited ? "NABL accredited" : "Not NABL accredited"}</span><span class="tag ${row.lab.home_collection ? "tag-home" : ""}">${row.lab.home_collection ? "Home collection" : "Visit lab"}</span><span class="tag">Collection ${rupees(row.lab.collection_fee)}</span><span class="tag">Report ~${esc(row.report_time_hours)}h</span></div>${placeMeta(row.lab)}</div><div class="place-price"><strong>${rupees(row.price)}</strong><small>test price · updated ${dateLabel(row.last_updated)}</small></div></article>`).join("")}</div>` : stateBox("empty", state.test.prices.length ? "No labs match these filters" : "No lab prices available", state.test.prices.length ? "Try turning off one of the filters." : "Lab prices will appear here when local data is available.")}
    </section>`;
}

function cartItems() {
  if (!cartCount()) return stateBox("empty", "Your estimate is empty", "Search for a medicine or test and add it here to compare costs.", '<button class="button-secondary" data-action="home">Search care options</button>');
  return `<div class="cart-list">${state.cart.medicines.map((item) => `<article class="cart-item"><span class="cart-item-icon">${icon("pill")}</span><div class="cart-item-main"><strong>${esc(item.name)}</strong><small>Medicine · MRP ${rupees(item.mrp)}</small></div><label class="qty-control"><span class="sr-only">Quantity</span><input type="number" min="1" max="1000" step="1" value="${item.qty}" data-qty="medicine" data-id="${item.id}" aria-label="Quantity for ${esc(item.name)}" /></label><button class="remove-button" data-action="remove-item" data-kind="medicine" data-id="${item.id}" aria-label="Remove ${esc(item.name)}">${icon("trash")}</button></article>`).join("")}${state.cart.tests.map((item) => `<article class="cart-item"><span class="cart-item-icon">${icon("flask")}</span><div class="cart-item-main"><strong>${esc(item.name)}</strong><small>Diagnostic test${item.fasting_required ? " · Confirm fasting instructions with lab" : ""}</small></div><button class="remove-button" data-action="remove-item" data-kind="test" data-id="${item.id}" aria-label="Remove ${esc(item.name)}">${icon("trash")}</button></article>`).join("")}</div>`;
}

function chartRow(label, value, max, kind) {
  const num = value == null ? null : Number(value);
  const width = num == null || !max ? 0 : Math.max(3, Math.min(100, num / max * 100));
  return `<div class="chart-row"><span>${label}</span><div class="chart-track"><div class="chart-fill ${kind}" style="width:${width}%"></div></div><strong>${rupees(value)}</strong></div>`;
}

function estimateSummary() {
  if (!cartCount()) return `<aside class="panel summary-panel"><h2>Your estimate</h2><p class="summary-subtitle">Your totals will appear here as you build a list.</p><div class="summary-total"><span>Current total</span><strong>₹0</strong></div></aside>`;
  if (state.estimate.status === "loading") return `<aside class="panel summary-panel"><h2>Your estimate</h2><p class="summary-subtitle">Comparing local options…</p>${stateBox("loading", "Calculating totals", "Checking pharmacy and lab prices.")}</aside>`;
  if (state.estimate.status === "error") return `<aside class="panel summary-panel"><h2>Your estimate</h2>${stateBox("error", "Estimate unavailable", state.estimate.error, '<button class="button-secondary" data-action="retry-estimate">Try again</button>')}</aside>`;
  const result = state.estimate.result;
  if (!result) return `<aside class="panel summary-panel"><h2>Your estimate</h2>${stateBox("loading", "Preparing estimate", "Checking prices.")}</aside>`;
  const med = result.medicines;
  const single = med.cheapest_single_pharmacy.total;
  const split = med.split_across_pharmacies.total;
  const bestLab = result.tests.best_single_lab;
  const reference = med.reference_estimate;
  const max = Math.max(Number(med.at_mrp) || 0, Number(reference?.total) || 0, Number(single) || 0, Number(split) || 0, 1);
  const savingsAmount = reference?.savings_vs_mrp?.amount == null ? null : Number(reference.savings_vs_mrp.amount);
  const referenceDifference = savingsAmount == null
    ? "—"
    : savingsAmount > 0
      ? `Lower by ${rupees(savingsAmount)} (${esc(reference.savings_vs_mrp.percent)}%)`
      : savingsAmount < 0
        ? `Higher by ${rupees(Math.abs(savingsAmount))} (${esc(Math.abs(Number(reference.savings_vs_mrp.percent)))}%)`
        : "Same as requested MRP";
  const alternativeItems = (reference?.items || []).filter((item) => item.selected_product?.name && item.selected_product.name !== item.name);
  return `<aside class="panel summary-panel"><h2>Your estimate</h2><p class="summary-subtitle">Catalogue reference prices are estimates; pharmacy totals require verified store quotes.</p>
    <div class="summary-total"><span>Requested medicines · catalogue MRP</span><strong>${rupees(med.at_mrp)}</strong></div>
    <div class="summary-line"><span>Reference estimate${state.useAlternatives ? " · cheapest compatible products" : " · selected products"}</span><strong>${rupees(reference?.total)}</strong></div>
    <div class="summary-line"><span>Cheapest single pharmacy quote</span><strong>${rupees(single)}</strong></div>
    <div class="summary-line"><span>Split pharmacy quotes</span><strong>${rupees(split)}</strong></div>
    <div class="summary-line"><span>Best single lab, incl. fee</span><strong>${rupees(bestLab?.total)}</strong></div>
    <div class="summary-line"><span>Tests, cheapest per lab</span><strong>${rupees(result.tests.cheapest_per_test_total)}</strong></div>
    <div class="summary-line"><span>Reference difference vs requested MRP</span><strong>${referenceDifference}</strong></div>
    <div class="chart"><div class="chart-title">MEDICINE PRICE OVERVIEW</div>${chartRow("Requested MRP", med.at_mrp, max, "mrp")}${chartRow("Reference estimate", reference?.total, max, "single")}${chartRow("One pharmacy quote", single, max, "single")}${chartRow("Split pharmacy quotes", split, max, "split")}</div>
    ${alternativeItems.length ? `<div class="estimate-tests"><h3>Products used in reference estimate</h3>${alternativeItems.map((item) => `<div class="estimate-test-line"><span>${esc(item.name)}<small style="display:block;margin-top:3px">Reference priced as ${esc(item.selected_product.name)}</small></span><strong>${rupees(item.total)}</strong></div>`).join("")}</div>` : ""}
    <div class="estimate-tests"><h3>Diagnostic tests</h3>${result.tests.cheapest_lab_per_test.length ? result.tests.cheapest_lab_per_test.map((item) => `<div class="estimate-test-line"><span>${esc(item.test_name)}${item.lab ? `<small style="display:block;margin-top:3px">${esc(item.lab.name)}</small>` : ""}</span><strong>${rupees(item.price)}</strong></div>`).join("") : `<div class="estimate-test-line"><span>No tests added</span><strong>—</strong></div>`}
      ${bestLab ? `<div class="estimate-test-line"><span>Best single lab · ${esc(bestLab.lab.name)}${Number(bestLab.collection_fee) ? ` incl. ${rupees(bestLab.collection_fee)} collection` : ""}</span><strong>${rupees(bestLab.total)}</strong></div>` : ""}
    </div>
    <div class="summary-total" style="margin-top:14px;margin-bottom:0"><span>Reference medicines + cheapest test labs</span><strong>${rupees(result.combined_grand_total.reference_medicines_plus_cheapest_test_labs)}</strong></div>
  </aside>`;
}

function estimatePage() {
  const subtitle = `${state.cart.medicines.length} medicines · ${state.cart.tests.length} tests`;
  return `${backHeader("Your estimate", subtitle)}<div class="estimate-layout"><section class="panel"><div class="section-title"><div><h2>Items in your list</h2><p>Update quantities or remove anything you don’t need</p></div><span class="count-pill">${cartCount()} items</span></div>
    ${cartItems()}
    ${state.cart.medicines.length ? `<div class="toggle-row"><div class="toggle-copy"><strong>Include medicine price matches</strong><small>Off by default. When enabled, the estimate uses the lowest compatible catalogue MRP normalized to the same pack size. It is not a pharmacy offer. Confirm any product change with your prescriber or pharmacist.</small></div><label class="switch"><input type="checkbox" data-toggle="alternatives" ${state.useAlternatives ? "checked" : ""} aria-label="Include medicine price matches"/><span class="switch-track"></span></label></div>` : ""}
  </section>${estimateSummary()}</div>`;
}

function render() {
  const page = state.page === "medicine" ? medicinePage()
    : state.page === "test" ? testPage()
      : state.page === "estimate" ? estimatePage()
        : homePage();
  root.innerHTML = `<div class="shell">${header()}${safetyNotice()}<main>${page}</main>${footer()}${mobileNav()}${state.toast ? `<div class="toast" role="status">${esc(state.toast)}</div>` : ""}</div>`;
}

let searchTimer;
let currentSearchVersion = 0;
async function doSearch(immediate = false) {
  window.clearTimeout(searchTimer);
  const version = ++currentSearchVersion;
  const query = state.query.trim();
  if (!query) {
    state.search = { status: "idle", results: [], error: "" };
    render();
    return;
  }
  const run = async () => {
    state.search = { status: "loading", results: [], error: "" };
    render();
    try {
      const results = await api(`/${state.searchMode}/search?q=${encodeURIComponent(query)}`);
      if (version !== currentSearchVersion) return;
      state.search = { status: results.length ? "success" : "empty", results, error: "" };
    } catch (error) {
      if (version !== currentSearchVersion) return;
      state.search = { status: "error", results: [], error: error.message };
    }
    render();
  };
  if (immediate) run(); else searchTimer = window.setTimeout(run, 300);
}

async function openMedicine(id) {
  state.page = "medicine";
  state.medicine = { id, status: "loading", detail: null, prices: [], error: "" };
  render();
  try {
    const [detail, prices] = await Promise.all([
      api(`/medicines/${id}/`), api(`/medicines/${id}/prices`),
    ]);
    state.medicine = { id, status: "success", detail, prices, error: "" };
  } catch (error) {
    state.medicine = { id, status: "error", detail: null, prices: [], error: error.message };
  }
  render();
}

async function openTest(id) {
  state.page = "test";
  state.test = { ...state.test, id, status: "loading", item: null, prices: [], error: "" };
  render();
  try {
    const cachedItem = state.search.results.find((row) => Number(row.id) === Number(id));
    const [searchResults, prices] = await Promise.all([
      api(`/tests/search?q=${encodeURIComponent(state.query || "")}`), api(`/tests/${id}/prices`),
    ]);
    const item = cachedItem || searchResults.find((row) => Number(row.id) === Number(id)) || { id, name: "Diagnostic test", category: "", aliases: "", fasting_required: false };
    state.test = { ...state.test, id, status: "success", item, prices, error: "" };
  } catch (error) {
    state.test = { ...state.test, id, status: "error", item: null, prices: [], error: error.message };
  }
  render();
}

function medicineSummary(id) {
  const current = state.medicine.detail?.medicine;
  if (current && Number(current.id) === Number(id)) return current;
  const alternative = state.medicine.detail?.alternatives?.find((item) => Number(item.id) === Number(id));
  if (alternative) return alternative;
  return state.search.results.find((item) => Number(item.id) === Number(id));
}

function addMedicine(id) {
  const item = medicineSummary(id);
  if (!item) return toast("Medicine details aren’t available yet.");
  const existing = state.cart.medicines.find((entry) => Number(entry.id) === Number(id));
  if (existing) existing.qty += 1;
  else state.cart.medicines.push({ id: Number(id), name: item.name, manufacturer: item.manufacturer || "", mrp: item.mrp, qty: 1 });
  saveCart(); render(); toast(`${item.name} added to your estimate`); updateEstimate();
}

function addTest(id) {
  let item = state.test.item && Number(state.test.item.id) === Number(id) ? state.test.item : null;
  if (!item) item = state.search.results.find((row) => Number(row.id) === Number(id));
  if (!item) return toast("Test details aren’t available yet.");
  if (!state.cart.tests.some((entry) => Number(entry.id) === Number(id))) {
    state.cart.tests.push({ id: Number(id), name: item.name, fasting_required: !!item.fasting_required });
  }
  saveCart(); render(); toast(`${item.name} added to your estimate`); updateEstimate();
}

function openEstimate() {
  state.page = "estimate";
  render();
  updateEstimate();
}

let estimateTimer;
async function updateEstimate() {
  window.clearTimeout(estimateTimer);
  if (!cartCount()) {
    state.estimate = { status: "idle", result: null, error: "" };
    if (state.page === "estimate") render();
    return;
  }
  const version = ++state.requestVersion;
  state.estimate = { status: "loading", result: state.estimate.result, error: "" };
  if (state.page === "estimate") render();
  estimateTimer = window.setTimeout(async () => {
    try {
      const result = await api("/estimate", {
        method: "POST",
        body: JSON.stringify({
          medicines: state.cart.medicines.map((item) => ({ id: item.id, qty: item.qty })),
          tests: state.cart.tests.map((item) => item.id),
          use_cheapest_alternatives: state.useAlternatives,
        }),
      });
      if (version !== state.requestVersion) return;
      state.estimate = { status: "success", result, error: "" };
    } catch (error) {
      if (version !== state.requestVersion) return;
      state.estimate = { status: "error", result: null, error: error.message };
    }
    if (state.page === "estimate") render();
  }, 80);
}

function setSearch(query, mode = state.searchMode, immediate = true) {
  currentSearchVersion += 1;
  state.searchMode = mode;
  state.query = query;
  state.page = "home";
  state.search = { status: "idle", results: [], error: "" };
  render();
  doSearch(immediate);
}

root.addEventListener("input", (event) => {
  if (event.target.id === "home-search") {
    state.query = event.target.value;
    doSearch(false);
  }
});

root.addEventListener("change", (event) => {
  if (event.target.matches("[data-filter='nabl']")) { state.test.nablOnly = event.target.checked; render(); }
  if (event.target.matches("[data-filter='home']")) { state.test.homeOnly = event.target.checked; render(); }
  if (event.target.matches("[data-toggle='alternatives']")) {
    state.useAlternatives = event.target.checked;
    updateEstimate();
  }
  if (event.target.matches("[data-qty]")) {
    const quantity = Math.max(1, Math.floor(Number(event.target.value) || 1));
    const collection = event.target.dataset.qty === "medicine" ? state.cart.medicines : state.cart.tests;
    const item = collection.find((entry) => Number(entry.id) === Number(event.target.dataset.id));
    if (item) item.qty = quantity;
    saveCart(); render(); updateEstimate();
  }
});

root.addEventListener("keydown", (event) => {
  if (event.target.id === "home-search" && event.key === "Enter") doSearch(true);
});

root.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const { action, id } = button.dataset;
  if (action === "home") { state.page = "home"; render(); }
  if (action === "estimate") openEstimate();
  if (action === "search-mode") {
    state.searchMode = button.dataset.mode;
    state.query = "";
    state.search = { status: "idle", results: [], error: "" };
    render();
  }
  if (action === "submit-search") doSearch(true);
  if (action === "clear-search") { state.query = ""; state.search = { status: "idle", results: [], error: "" }; render(); }
  if (action === "search-chip" || action === "popular") setSearch(button.dataset.query, button.dataset.mode || state.searchMode, true);
  if (action === "retry-search") doSearch(true);
  if (action === "open-medicine") openMedicine(id);
  if (action === "open-test") openTest(id);
  if (action === "add-medicine") addMedicine(id);
  if (action === "add-test") addTest(id);
  if (action === "retry-medicine") openMedicine(state.medicine.id);
  if (action === "retry-test") openTest(state.test.id);
  if (action === "retry-estimate") updateEstimate();
  if (action === "remove-item") {
    const key = button.dataset.kind === "medicine" ? "medicines" : "tests";
    state.cart[key] = state.cart[key].filter((item) => Number(item.id) !== Number(id));
    saveCart(); render(); updateEstimate();
  }
});

render();
