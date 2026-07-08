import threading
import time
import json
import traceback
from datetime import datetime
from tkinter import filedialog
import tkinter.messagebox as messagebox

try:
    import customtkinter as ctk
    import pandas as pd
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium_stealth import stealth
    import cloudscraper
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise SystemExit(
        f"Missing dependency: {e}\n"
        "Please install requirements using:\n"
        "pip install customtkinter pandas selenium webdriver-manager selenium-stealth cloudscraper beautifulsoup4 curl_cffi"
    )

# ==============================================================================
# UI COLOR PALETTE CONFIGURATION
# ==============================================================================
BG_MAIN     = "#FBEFEF"
BG_CARD     = "#FFE2E2"
ACCENT      = "#C5B3D3"
HOVER       = "#F5CBCB"
TEXT_ACTIVE = "#4A3E4E"
BG_INPUT    = "#FFFFFF"

# ==============================================================================
# MAIN APPLICATION CLASS
# ==============================================================================
class ScripyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure application window
        self.title("Scripy - Dynamic Data Engine")
        self.geometry("850x750")
        self.minsize(700, 650)
        
        # Set light mode and apply main background color
        ctk.set_appearance_mode("light")
        self.configure(fg_color=BG_MAIN)
        
        # Fonts
        self.font_header = ctk.CTkFont(family="Helvetica", size=26, weight="bold")
        self.font_subtitle = ctk.CTkFont(family="Helvetica", size=14)
        self.font_label = ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        self.font_entry = ctk.CTkFont(family="Helvetica", size=13)
        self.font_btn = ctk.CTkFont(family="Helvetica", size=15, weight="bold")
        self.font_log = ctk.CTkFont(family="Consolas", size=12)
        
        self.build_ui()
        self.log("System initialized. Ultra-Fast JS Extraction Engine ready.")

    def build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(30, 20))
        
        ctk.CTkLabel(
            header_frame, 
            text="SCRIPY - DYNAMIC DATA ENGINE", 
            font=self.font_header, 
            text_color=TEXT_ACTIVE
        ).pack()
        
        ctk.CTkLabel(
            header_frame, 
            text="Universal Headless Web Scraper (Clean, Fast, Error-Free)", 
            font=self.font_subtitle, 
            text_color=TEXT_ACTIVE
        ).pack(pady=(5, 0))

        settings_frame = ctk.CTkFrame(
            self, 
            fg_color=BG_CARD, 
            corner_radius=12, 
            border_width=2, 
            border_color=ACCENT
        )
        settings_frame.pack(fill="x", padx=40, pady=10)
        
        input_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        input_container.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            input_container, 
            text="Target URL:", 
            font=self.font_label, 
            text_color=TEXT_ACTIVE
        ).pack(side="left", padx=(0, 15))
        
        self.url_entry = ctk.CTkEntry(
            input_container, 
            fg_color=BG_INPUT, 
            text_color=TEXT_ACTIVE, 
            border_color=ACCENT,
            border_width=2,
            font=self.font_entry,
            placeholder_text="Paste any website URL (e.g. books.toscrape.com)..."
        )
        self.url_entry.pack(side="left", fill="x", expand=True)

        radio_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        radio_container.pack(fill="x", padx=20, pady=(10, 10))
        
        ctk.CTkLabel(
            radio_container, 
            text="Export Format:", 
            font=self.font_label, 
            text_color=TEXT_ACTIVE
        ).pack(side="left", padx=(0, 15))
        
        self.format_var = ctk.StringVar(value="CSV")
        
        ctk.CTkRadioButton(
            radio_container, 
            text="CSV Spreadsheet", 
            variable=self.format_var, 
            value="CSV",
            fg_color=ACCENT, 
            hover_color=HOVER, 
            border_color=ACCENT,
            text_color=TEXT_ACTIVE,
            font=self.font_entry
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            radio_container, 
            text="JSON Structured", 
            variable=self.format_var, 
            value="JSON",
            fg_color=ACCENT, 
            hover_color=HOVER, 
            border_color=ACCENT,
            text_color=TEXT_ACTIVE,
            font=self.font_entry
        ).pack(side="left", padx=10)
        
        toggle_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        toggle_container.pack(fill="x", padx=20, pady=(0, 20))

        self.headless_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            toggle_container,
            text="Run in Headless Mode (Disable for advanced bypass)",
            variable=self.headless_var,
            font=self.font_entry,
            text_color=TEXT_ACTIVE,
            progress_color=ACCENT
        ).pack(side="left", padx=(0, 15))

        self.exec_btn = ctk.CTkButton(
            self, 
            text="Execute Web Scraping", 
            font=self.font_btn,
            fg_color=ACCENT, 
            hover_color=HOVER, 
            text_color=TEXT_ACTIVE,
            height=50,
            corner_radius=10,
            command=self.on_execute_click
        )
        self.exec_btn.pack(pady=(20, 10))

        log_container = ctk.CTkFrame(
            self, 
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=2,
            border_color=ACCENT
        )
        log_container.pack(fill="both", expand=True, padx=40, pady=(10, 30))
        
        terminal_label = ctk.CTkLabel(
            log_container, 
            text="TELEMETRY TERMINAL", 
            font=ctk.CTkFont(family="Helvetica", size=11, weight="bold"), 
            text_color=TEXT_ACTIVE
        )
        terminal_label.pack(anchor="w", padx=15, pady=(10, 0))
        
        self.terminal = ctk.CTkTextbox(
            log_container, 
            fg_color=BG_INPUT, 
            text_color=TEXT_ACTIVE, 
            font=self.font_log,
            border_width=0,
            corner_radius=8
        )
        self.terminal.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.terminal.configure(state="disabled")

    def log(self, message: str):
        """Thread-safe UI log updater."""
        def _insert():
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"[{timestamp}] Scripy: {message}\n"
            self.terminal.configure(state="normal")
            self.terminal.insert("end", formatted_msg)
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        self.after(0, _insert)

    def on_execute_click(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("ERROR: Target URL cannot be empty. Please provide a valid URL.")
            return
            
        if not url.startswith("http"):
            url = "https://" + url
            
        self.exec_btn.configure(text="Scraping Active...", state="disabled")
        self.url_entry.configure(state="disabled")
        
        self.log("Initializing background thread for blazing fast scraping...")
        
        scraper_thread = threading.Thread(
            target=self.run_dynamic_scraper, 
            args=(url,), 
            daemon=True
        )
        scraper_thread.start()

    def reset_ui_state(self):
        def _reset():
            self.exec_btn.configure(text="Execute Web Scraping", state="normal")
            self.url_entry.configure(state="normal")
        self.after(0, _reset)

    def run_dynamic_scraper(self, target_url: str):
        self.log("Launching background driver...")
        
        options = Options()
        if self.headless_var.get():
            options.add_argument("--headless=new")
        options.add_argument("--incognito")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = None
        scraped_data = []
        
        try:
            try:
                driver = webdriver.Chrome(options=options)
            except Exception:
                self.log("Falling back to webdriver-manager...")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            
            # Stealth Injection
            stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            
            self.log(f"Navigating to {target_url}...")
            driver.set_page_load_timeout(30)
            
            try:
                driver.get(target_url)
            except Exception as e:
                self.log(f"Warning on page load: {e}")
            
            self.log("Waiting 8 seconds for security handshakes and heavy layouts to render...")
            time.sleep(8)
            
            self.log("Scrolling to load dynamic content...")
            # Optimized Smart Scrolling
            last_height = driver.execute_script("return document.body.scrollHeight")
            for _ in range(4):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                    
            self.log("Extracting DOM via high-performance JavaScript pipeline...")
            
            # JS Extractor is 100x faster and immune to StaleElementReferenceException
            js_extractor = """
            return (function() {
                let results = [];
                let currencyRegex = /([$£€₹]|Rs\.?)\\s*\\d+([.,]\\d+)?|\\d+([.,]\\d+)?\\s*([$£€₹]|Rs\.?)/i;
                let cards = document.querySelectorAll("article, .product, .item, .card, li, [class*='product'], [class*='item']");
                let processedTexts = new Set();
                
                for (let card of cards) {
                    let text = card.innerText || "";
                    text = text.trim();
                    if (text.length < 5) continue;
                    
                    let textSnippet = text.substring(0, 100);
                    if (processedTexts.has(textSnippet)) continue;
                    processedTexts.add(textSnippet);
                    
                    let img = card.querySelector("img");
                    let link = card.querySelector("a");
                    
                    let match = text.match(currencyRegex);
                    let price = match ? match[0] : "N/A";
                    
                    let imgUrl = "N/A";
                    if (img) {
                        imgUrl = img.getAttribute("src") || img.getAttribute("data-src") || img.currentSrc || "N/A";
                        if (imgUrl.startsWith("data:image")) imgUrl = "Base64 Image Data";
                    } else {
                        let bgDiv = card.querySelector("[style*='background-image']");
                        if (bgDiv) {
                            let style = window.getComputedStyle(bgDiv).backgroundImage;
                            let m = style.match(/url\\(['"]?(.*?)['"]?\\)/);
                            if (m) imgUrl = m[1];
                        }
                    }
                    
                    let href = link ? link.href : "N/A";
                    let titleElem = card.querySelector("h1, h2, h3, h4, h5, h6, .title, [class*='name']");
                    let title = titleElem ? titleElem.innerText.trim() : text.split('\\n')[0].trim();
                    if (!title) title = "Unknown Item";
                    
                    if (href !== "N/A" || imgUrl !== "N/A" || price !== "N/A") {
                        results.push({
                            "Type": price !== "N/A" ? "Product Card" : "List Item",
                            "Title_or_Text": title.substring(0, 200).replace(/\\n/g, ' | '),
                            "Price_or_Data": price,
                            "URL_Link": href,
                            "Image_URL": imgUrl
                        });
                    }
                }
                
                if (results.length === 0) {
                    let links = document.querySelectorAll("a");
                    let seenLinks = new Set();
                    for (let a of links) {
                        if (a.href && a.href.startsWith("http") && !seenLinks.has(a.href)) {
                            seenLinks.add(a.href);
                            results.push({
                                "Type": "Raw Hyperlink",
                                "Title_or_Text": (a.innerText || "Link").trim().substring(0, 200).replace(/\\n/g, ' | '),
                                "Price_or_Data": "N/A",
                                "URL_Link": a.href,
                                "Image_URL": "N/A"
                            });
                        }
                    }
                }
                return results;
            })();
            """
            
            scraped_data = driver.execute_script(js_extractor)
            
            if scraped_data:
                self.log(f"Extraction Complete! Collected {len(scraped_data)} records instantly.")
            else:
                self.log("FATAL: Page is entirely blank, heavily protected, or contains zero valid links.")
                raise Exception("No data extracted by Javascript")

        except Exception as e:
            self.log(f"Browser extraction failed/blocked: {str(e)}")
            self.log("Activating Advanced TLS Fallback (curl_cffi)...")
            try:
                html_response = curl_requests.get(target_url, impersonate="chrome120", timeout=20)
                
                if html_response.status_code != 200:
                    self.log(f"TLS Fallback returned {html_response.status_code}. Trying Cloudscraper...")
                    scraper = cloudscraper.create_scraper(
                        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
                    )
                    html_response = scraper.get(target_url, timeout=20)
                    
                if html_response.status_code == 200:
                    soup = BeautifulSoup(html_response.text, "html.parser")
                    
                    # Fallback extraction logic
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if not href.startswith('http'):
                            href = target_url.rstrip('/') + '/' + href.lstrip('/')
                            
                        text = a.get_text(strip=True) or "Extracted Link"
                        if len(href) > 5 and len(text) > 2:
                            scraped_data.append({
                                "Type": "Static Fallback Data",
                                "Title_or_Text": text[:200],
                                "Price_or_Data": "N/A",
                                "URL_Link": href,
                                "Image_URL": "N/A"
                            })
                    
                    # Deduplicate fallback data based on URL
                    unique_data = {item["URL_Link"]: item for item in scraped_data}
                    scraped_data = list(unique_data.values())
                    
                    if scraped_data:
                        self.log(f"Fallback SUCCESS: Extracted {len(scraped_data)} links via static parsing.")
                    else:
                        self.log("Fallback FAILURE: No valid links could be extracted statically.")
                else:
                    self.log(f"Fallback blocked with status code: {html_response.status_code}")
            except Exception as fb_err:
                self.log(f"CRITICAL ERROR during fallback: {str(fb_err)}")
                traceback.print_exc()
        finally:
            if driver:
                self.log("Closing web driver...")
                driver.quit()
                
            if scraped_data:
                self.after(0, self.prompt_export, scraped_data)
            else:
                self.reset_ui_state()

    def prompt_export(self, data: list):
        export_format = self.format_var.get()
        self.log(f"Opening save dialog for {export_format} export...")
        
        if export_format == "CSV":
            file_types = [("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
            default_ext = ".csv"
        else:
            file_types = [("JSON Structured", "*.json"), ("All Files", "*.*")]
            default_ext = ".json"
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Scripy_Export_{timestamp}{default_ext}"

        # CRITICAL FIX: parent=self ensures dialog doesn't get buried behind the main window
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save Extracted Data",
            defaultextension=default_ext,
            filetypes=file_types,
            initialfile=default_filename
        )

        if filepath:
            try:
                if export_format == "CSV":
                    df = pd.DataFrame(data)
                    df.to_csv(filepath, index=False, encoding='utf-8-sig')
                else:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                        
                self.log(f"SUCCESS: Dataset saved to {filepath}")
                messagebox.showinfo("Success", f"Data successfully saved to:\n{filepath}", parent=self)
            except Exception as e:
                self.log(f"ERROR: Failed to save file - {e}")
                messagebox.showerror("Error", f"Failed to save file:\n{e}", parent=self)
        else:
            self.log("Export operation cancelled by user.")
            
        self.reset_ui_state()

if __name__ == "__main__":
    app = ScripyApp()
    app.mainloop()
