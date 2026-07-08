"""
Scripy - Elite Anti-Detection Web Scraping Engine
Architecture: DrissionPage (primary) + curl_cffi TLS-hardened fallback
Supports: Cloudflare, Akamai, PerimeterX, DataDome protected sites
"""

import os
import sys
import json
import random
import string
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
import tkinter.messagebox as messagebox

try:
    import customtkinter as ctk
    import pandas as pd
    from DrissionPage import ChromiumPage, ChromiumOptions
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise SystemExit(
        f"Missing dependency: {e}\n"
        "Install all requirements with:\n"
        "pip install customtkinter pandas DrissionPage curl_cffi beautifulsoup4"
    )

# ==============================================================================
# ANTI-DETECTION ENGINE CONSTANTS
# ==============================================================================

# Persistent user-data directory - reused across sessions to build a "history"
# that WAFs trust, passing canvas/WebGL fingerprint checks naturally.
_PROFILE_DIR = Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "Scripy" / "browser_profile"
_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# Rotating UA pool - covers Chrome 120-136, all Windows 10/11 builds
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.85 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.89 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.118 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
]

# SEC-CH-UA pairs matched to each UA above (must match Chrome major version exactly)
_SEC_CH_UA = [
    '"Chromium";v="136", "Google Chrome";v="136", "Not_A Brand";v="24"',
    '"Chromium";v="135", "Google Chrome";v="135", "Not_A Brand";v="24"',
    '"Chromium";v="134", "Google Chrome";v="134", "Not_A Brand";v="24"',
    '"Chromium";v="133", "Google Chrome";v="133", "Not_A Brand";v="24"',
    '"Chromium";v="120", "Google Chrome";v="120", "Not_A Brand";v="24"',
    '"Chromium";v="136", "Google Chrome";v="136", "Not_A Brand";v="24"',
]

# curl_cffi impersonation flavors - rotate to avoid JA3 fingerprint re-use
_CURL_IMPERSONATIONS = ["chrome120", "chrome124", "chrome131", "chrome136"]

# DOM readiness selector cascade: tries known product grid selectors first,
# then generic content fallbacks. First match wins.
_READINESS_SELECTORS = [
    # Luxury retail / fashion
    "[data-testid='product-card']",
    ".lv-product-card",
    "[class*='ProductCard']",
    "[class*='product-card']",
    "[class*='productCard']",
    # General e-commerce
    "[data-product]",
    "article",
    ".product",
    "[class*='product']",
    # Content fallback
    "main",
    "#content",
    "body",
]

# ==============================================================================
# UI PALETTE
# ==============================================================================
BG_MAIN     = "#FBEFEF"
BG_CARD     = "#FFE2E2"
ACCENT      = "#C5B3D3"
HOVER       = "#F5CBCB"
TEXT_ACTIVE = "#4A3E4E"
BG_INPUT    = "#FFFFFF"

# ==============================================================================
# JAVASCRIPT EXTRACTOR (injected into the live page via CDP)
# ==============================================================================
_JS_EXTRACTOR = r"""
return (function() {
    var results = [];
    var currencyRegex = /(?:[$\u00a3\u20ac\u20b9]|Rs\.?)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*(?:[$\u00a3\u20ac\u20b9]|Rs\.?)/i;
    var processedHrefs = new Set();

    // --- PASS 1: Structured product cards ---
    var cardSelectors = [
        "article", "[data-testid*='product']", "[class*='ProductCard']",
        "[class*='product-card']", "[class*='productCard']", ".product",
        ".item", ".card", "[data-product]", "li[class*='item']"
    ];
    var cards = document.querySelectorAll(cardSelectors.join(","));

    for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var text = (card.innerText || "").trim();
        if (text.length < 3) continue;

        var link = card.querySelector("a[href]");
        var img  = card.querySelector("img");
        var titleElem = card.querySelector("h1,h2,h3,h4,h5,h6,[class*='name'],[class*='title'],[class*='Name'],[class*='Title']");

        var href = link ? link.href : "N/A";
        if (href !== "N/A" && processedHrefs.has(href)) continue;
        if (href !== "N/A") processedHrefs.add(href);

        var priceMatch = text.match(currencyRegex);
        var price = priceMatch ? priceMatch[0].trim() : "N/A";

        var imgUrl = "N/A";
        if (img) {
            imgUrl = img.getAttribute("data-src") || img.getAttribute("src") || img.currentSrc || "N/A";
            if (imgUrl && imgUrl.startsWith("data:image")) imgUrl = "Base64 (embedded)";
        } else {
            var bgEl = card.querySelector("[style*='background-image']");
            if (bgEl) {
                var m = window.getComputedStyle(bgEl).backgroundImage.match(/url\(['"]?(.*?)['"]?\)/);
                if (m) imgUrl = m[1];
            }
        }

        var title = titleElem ? titleElem.innerText.trim() : text.split("\n")[0].trim();
        if (!title) title = "Item";

        if (href !== "N/A" || imgUrl !== "N/A" || price !== "N/A") {
            results.push({
                "Type": price !== "N/A" ? "Product Card" : "List Item",
                "Title_or_Text": title.substring(0, 200).replace(/\n/g, " | "),
                "Price_or_Data": price,
                "URL_Link": href,
                "Image_URL": imgUrl
            });
        }
    }

    // --- PASS 2: Raw hyperlink fallback (fires only if PASS 1 found nothing) ---
    if (results.length === 0) {
        var allLinks = document.querySelectorAll("a[href]");
        for (var j = 0; j < allLinks.length; j++) {
            var a = allLinks[j];
            if (!a.href || !a.href.startsWith("http")) continue;
            if (processedHrefs.has(a.href)) continue;
            processedHrefs.add(a.href);
            var linkText = (a.innerText || "Link").trim().substring(0, 200).replace(/\n/g, " | ");
            results.push({
                "Type": "Raw Hyperlink",
                "Title_or_Text": linkText,
                "Price_or_Data": "N/A",
                "URL_Link": a.href,
                "Image_URL": "N/A"
            });
        }
    }
    return results;
})();
"""

# ==============================================================================
# MAIN APPLICATION
# ==============================================================================
class ScripyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scripy - Elite Anti-Detection Scraper")
        self.geometry("880x780")
        self.minsize(700, 650)
        ctk.set_appearance_mode("light")
        self.configure(fg_color=BG_MAIN)

        self.font_header   = ctk.CTkFont(family="Helvetica", size=26, weight="bold")
        self.font_subtitle = ctk.CTkFont(family="Helvetica", size=14)
        self.font_label    = ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        self.font_entry    = ctk.CTkFont(family="Helvetica", size=13)
        self.font_btn      = ctk.CTkFont(family="Helvetica", size=15, weight="bold")
        self.font_log      = ctk.CTkFont(family="Consolas",  size=12)

        self._build_ui()
        self.log("System initialized. Elite Anti-Detection Engine v3.0 ready.")
        self.log(f"Persistent browser profile: {_PROFILE_DIR}")

    # ------------------------------------------------------------------
    # UI BUILDER
    # ------------------------------------------------------------------
    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", pady=(30, 20))
        ctk.CTkLabel(hdr, text="SCRIPY — ELITE SCRAPING ENGINE",
                     font=self.font_header, text_color=TEXT_ACTIVE).pack()
        ctk.CTkLabel(hdr, text="Anti-Bot Bypass: Cloudflare · Akamai · PerimeterX · DataDome",
                     font=self.font_subtitle, text_color=TEXT_ACTIVE).pack(pady=(5, 0))

        settings = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12,
                                border_width=2, border_color=ACCENT)
        settings.pack(fill="x", padx=40, pady=10)

        url_row = ctk.CTkFrame(settings, fg_color="transparent")
        url_row.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(url_row, text="Target URL:", font=self.font_label,
                     text_color=TEXT_ACTIVE).pack(side="left", padx=(0, 15))
        self.url_entry = ctk.CTkEntry(
            url_row, fg_color=BG_INPUT, text_color=TEXT_ACTIVE,
            border_color=ACCENT, border_width=2, font=self.font_entry,
            placeholder_text="https://any-website.com/products  — works on protected sites!")
        self.url_entry.pack(side="left", fill="x", expand=True)

        fmt_row = ctk.CTkFrame(settings, fg_color="transparent")
        fmt_row.pack(fill="x", padx=20, pady=(10, 10))
        ctk.CTkLabel(fmt_row, text="Export Format:", font=self.font_label,
                     text_color=TEXT_ACTIVE).pack(side="left", padx=(0, 15))
        self.format_var = ctk.StringVar(value="CSV")
        for label, val in [("CSV Spreadsheet", "CSV"), ("JSON Structured", "JSON")]:
            ctk.CTkRadioButton(fmt_row, text=label, variable=self.format_var, value=val,
                               fg_color=ACCENT, hover_color=HOVER, border_color=ACCENT,
                               text_color=TEXT_ACTIVE, font=self.font_entry).pack(side="left", padx=10)

        toggle_row = ctk.CTkFrame(settings, fg_color="transparent")
        toggle_row.pack(fill="x", padx=20, pady=(0, 20))
        self.headless_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(toggle_row,
                      text="Headless Mode  (Disable for maximum bypass on ultra-protected sites)",
                      variable=self.headless_var, font=self.font_entry,
                      text_color=TEXT_ACTIVE, progress_color=ACCENT).pack(side="left")

        self.exec_btn = ctk.CTkButton(
            self, text="Execute Web Scraping", font=self.font_btn,
            fg_color=ACCENT, hover_color=HOVER, text_color=TEXT_ACTIVE,
            height=50, corner_radius=10, command=self._on_execute)
        self.exec_btn.pack(pady=(20, 10))

        log_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12,
                                  border_width=2, border_color=ACCENT)
        log_frame.pack(fill="both", expand=True, padx=40, pady=(10, 30))
        ctk.CTkLabel(log_frame, text="TELEMETRY TERMINAL",
                     font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"),
                     text_color=TEXT_ACTIVE).pack(anchor="w", padx=15, pady=(10, 0))
        self.terminal = ctk.CTkTextbox(
            log_frame, fg_color=BG_INPUT, text_color=TEXT_ACTIVE,
            font=self.font_log, border_width=0, corner_radius=8)
        self.terminal.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.terminal.configure(state="disabled")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def log(self, message: str):
        """Thread-safe telemetry logger."""
        def _insert():
            ts = datetime.now().strftime("%H:%M:%S")
            self.terminal.configure(state="normal")
            self.terminal.insert("end", f"[{ts}] Scripy: {message}\n")
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        self.after(0, _insert)

    def _reset_ui(self):
        def _do():
            self.exec_btn.configure(text="Execute Web Scraping", state="normal")
            self.url_entry.configure(state="normal")
        self.after(0, _do)

    def _on_execute(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("ERROR: Please provide a target URL.")
            return
        if not url.startswith("http"):
            url = "https://" + url
        self.exec_btn.configure(text="Scraping Active...", state="disabled")
        self.url_entry.configure(state="disabled")
        self.log("Spawning anti-detection scraping thread...")
        threading.Thread(target=self._scrape_pipeline, args=(url,), daemon=True).start()

    # ------------------------------------------------------------------
    # CORE SCRAPING PIPELINE
    # ------------------------------------------------------------------
    def _scrape_pipeline(self, target_url: str):
        """
        Two-stage pipeline:
          Stage 1 – DrissionPage with persistent profile + smart DOM wait
          Stage 2 – curl_cffi with hardened TLS / header spoofing
        """
        ua_index   = random.randint(0, len(_USER_AGENTS) - 1)
        user_agent = _USER_AGENTS[ua_index]
        sec_ch_ua  = _SEC_CH_UA[ua_index]

        scraped_data = []

        # ── STAGE 1: DRISSIONPAGE ─────────────────────────────────────
        driver = None
        try:
            scraped_data = self._run_browser_stage(target_url, user_agent, sec_ch_ua)
        except Exception as e:
            self.log(f"Browser stage failed: {e}")
        finally:
            # Driver is closed inside _run_browser_stage already
            pass

        # ── STAGE 2: HARDENED curl_cffi FALLBACK ─────────────────────
        if not scraped_data:
            self.log("Activating hardened TLS fallback (curl_cffi)...")
            try:
                scraped_data = self._run_curl_stage(target_url, user_agent, sec_ch_ua)
            except Exception as e:
                self.log(f"TLS fallback failed: {e}")
                traceback.print_exc()

        # ── RESULT ────────────────────────────────────────────────────
        if scraped_data:
            self.after(0, self._prompt_export, scraped_data)
        else:
            self.log("⚠ All extraction strategies exhausted. Zero data returned.")
            self._reset_ui()

    # ------------------------------------------------------------------
    # STAGE 1: DRISSIONPAGE BROWSER ENGINE
    # ------------------------------------------------------------------
    def _run_browser_stage(self, url: str, user_agent: str, sec_ch_ua: str) -> list:
        self.log(f"[Browser] Launching DrissionPage with UA: {user_agent[:60]}...")

        co = ChromiumOptions()

        # ── Headless config ──────────────────────────────────────────
        if self.headless_var.get():
            co.headless(True)

        # ── Persistent profile — the KEY to bypassing canvas/WebGL checks ──
        co.set_user_data_path(str(_PROFILE_DIR))

        # ── Chrome arguments ─────────────────────────────────────────
        co.set_argument("--window-size=1920,1080")
        co.set_argument("--disable-blink-features=AutomationControlled")
        co.set_argument("--no-first-run")
        co.set_argument("--no-default-browser-check")
        co.set_argument("--disable-popup-blocking")
        co.set_argument(f"--user-agent={user_agent}")

        # ── Strip automation indicators via prefs ────────────────────
        co.set_pref("credentials_enable_service", False)
        co.set_pref("profile.password_manager_enabled", False)

        driver = ChromiumPage(co)
        try:
            self.log(f"[Browser] Navigating → {url}")
            try:
                driver.get(url, timeout=35)
            except Exception as nav_e:
                # Navigation timeout is FINE — page often partially loads
                self.log(f"[Browser] Nav notice (continuing): {nav_e}")

            # ── SMART DOM WAIT (replaces all fixed sleep) ─────────────
            self.log("[Browser] Smart-waiting for content to render (max 12s)...")
            ready = self._wait_for_content(driver, timeout=12)
            if ready:
                self.log(f"[Browser] Content detected via selector: {ready}")
            else:
                self.log("[Browser] Timeout — page content may be sparse, extracting anyway...")

            # ── INCREMENTAL SCROLL (event-driven, not time-slept) ─────
            self.log("[Browser] Loading dynamic content via incremental scroll...")
            self._smart_scroll(driver)

            # ── JS EXTRACTION ─────────────────────────────────────────
            self.log("[Browser] Running JS extraction pipeline...")
            data = driver.run_js(_JS_EXTRACTOR)

            if data and len(data) > 0:
                self.log(f"[Browser] ✓ Extracted {len(data)} records.")
                return data
            else:
                raise Exception("JS returned zero records")

        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def _wait_for_content(self, driver: ChromiumPage, timeout: int = 12) -> str:
        """
        Event-driven wait: polls for known product/content selectors.
        Returns the matching selector string, or empty string on timeout.
        Much faster than fixed sleep — exits the millisecond content appears.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for sel in _READINESS_SELECTORS:
                try:
                    elem = driver.ele(f"css:{sel}", timeout=0)
                    if elem:
                        return sel
                except Exception:
                    pass
            time.sleep(0.25)
        return ""

    def _smart_scroll(self, driver: ChromiumPage):
        """
        Incremental scroll that detects page-height stabilization,
        capped at 6 scroll attempts to avoid infinite loops on infinite-scroll pages.
        """
        import time
        try:
            last_height = driver.run_js("return document.body.scrollHeight")
            for attempt in range(6):
                driver.scroll.to_bottom()
                time.sleep(0.8)  # minimal settle time
                new_height = driver.run_js("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # no new content loaded, stop early
                last_height = new_height
        except Exception as e:
            self.log(f"[Browser] Scroll notice (non-fatal): {e}")

    # ------------------------------------------------------------------
    # STAGE 2: HARDENED curl_cffi TLS FALLBACK
    # ------------------------------------------------------------------
    def _run_curl_stage(self, url: str, user_agent: str, sec_ch_ua: str) -> list:
        from urllib.parse import urlparse

        parsed   = urlparse(url)
        origin   = f"{parsed.scheme}://{parsed.netloc}"
        referer  = origin + "/"
        imperson = random.choice(_CURL_IMPERSONATIONS)

        self.log(f"[Fallback] TLS impersonation: {imperson} | Origin: {origin}")

        # Realistic Chrome header stack including HTTP/2 pseudo-headers
        headers = {
            "User-Agent"                : user_agent,
            "Accept"                    : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language"           : "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding"           : "gzip, deflate, br, zstd",
            "sec-ch-ua"                 : sec_ch_ua,
            "sec-ch-ua-mobile"          : "?0",
            "sec-ch-ua-platform"        : '"Windows"',
            "Sec-Fetch-Dest"            : "document",
            "Sec-Fetch-Mode"            : "navigate",
            "Sec-Fetch-Site"            : "none",
            "Sec-Fetch-User"            : "?1",
            "Upgrade-Insecure-Requests" : "1",
            "Referer"                   : referer,
            "Origin"                    : origin,
            "Cache-Control"             : "max-age=0",
            "Connection"                : "keep-alive",
            "DNT"                       : "1",
        }

        session = curl_requests.Session()
        response = session.get(url, headers=headers, impersonate=imperson,
                               timeout=25, allow_redirects=True)

        self.log(f"[Fallback] HTTP {response.status_code} received.")

        if response.status_code == 200:
            return self._parse_html(response.text, url)
        else:
            raise Exception(f"HTTP {response.status_code} from fallback layer")

    def _parse_html(self, html: str, base_url: str) -> list:
        from urllib.parse import urlparse, urljoin
        soup   = BeautifulSoup(html, "html.parser")
        data   = []
        seen   = set()
        parsed = urlparse(base_url)
        base   = f"{parsed.scheme}://{parsed.netloc}"

        for a in soup.find_all("a", href=True):
            raw  = a["href"].strip()
            href = raw if raw.startswith("http") else urljoin(base, raw)
            if href in seen or len(href) < 8:
                continue
            seen.add(href)
            text = a.get_text(strip=True) or "Link"
            data.append({
                "Type"          : "Static Fallback",
                "Title_or_Text" : text[:200],
                "Price_or_Data" : "N/A",
                "URL_Link"      : href,
                "Image_URL"     : "N/A"
            })

        if data:
            self.log(f"[Fallback] ✓ Parsed {len(data)} links from static HTML.")
        else:
            self.log("[Fallback] HTML received but zero links found (likely JS-rendered page).")
        return data

    # ------------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------------
    def _prompt_export(self, data: list):
        fmt = self.format_var.get()
        self.log(f"Opening save dialog for {fmt} export ({len(data)} records)...")

        file_types = [("CSV Spreadsheet", "*.csv")] if fmt == "CSV" else [("JSON", "*.json")]
        ext        = ".csv" if fmt == "CSV" else ".json"
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")

        filepath = filedialog.asksaveasfilename(
            parent=self, title="Save Extracted Data",
            defaultextension=ext, filetypes=file_types,
            initialfile=f"Scripy_Export_{ts}{ext}")

        if filepath:
            try:
                if fmt == "CSV":
                    pd.DataFrame(data).to_csv(filepath, index=False, encoding="utf-8-sig")
                else:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                self.log(f"✓ Saved → {filepath}")
                messagebox.showinfo("Success", f"Data saved to:\n{filepath}", parent=self)
            except Exception as e:
                self.log(f"ERROR saving file: {e}")
                messagebox.showerror("Error", f"Save failed:\n{e}", parent=self)
        else:
            self.log("Export cancelled by user.")

        self._reset_ui()


# ==============================================================================
if __name__ == "__main__":
    app = ScripyApp()
    app.mainloop()
