import threading
import time
import json
import re
import traceback
from datetime import datetime
from tkinter import filedialog

try:
    import customtkinter as ctk
    import pandas as pd
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    raise SystemExit(
        f"Missing dependency: {e}\n"
        "Please install requirements using:\n"
        "pip install customtkinter pandas selenium webdriver-manager"
    )

# ==============================================================================
# UI COLOR PALETTE CONFIGURATION (Strict Match: Color Hunt Palette)
# ==============================================================================
BG_MAIN     = "#FBEFEF"  # Application Main Background canvas color
BG_CARD     = "#FFE2E2"  # Information Display Cards frame backgrounds
ACCENT      = "#C5B3D3"  # Interactive System Buttons & Accent Borders
HOVER       = "#F5CBCB"  # Interactive Buttons Hover-State change color
TEXT_ACTIVE = "#4A3E4E"  # Active Font Color (high-contrast deep mauve/charcoal)
BG_INPUT    = "#FFFFFF"  # Clean white for text entry

# ==============================================================================
# MAIN APPLICATION CLASS
# ==============================================================================
class ScripyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure application window
        self.title("Scripy - Dynamic Data Engine")
        self.geometry("850x700")
        self.minsize(700, 600)
        
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
        self.log("System initialized. 3-Tier Universal Extraction Engine ready.")

    def build_ui(self):
        # ---------------------------------------------------------
        # Header Matrix
        # ---------------------------------------------------------
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
            text="Universal Headless Web Scraper (Never Comes Empty Handed)", 
            font=self.font_subtitle, 
            text_color=TEXT_ACTIVE
        ).pack(pady=(5, 0))

        # ---------------------------------------------------------
        # Content Settings Panel
        # ---------------------------------------------------------
        settings_frame = ctk.CTkFrame(
            self, 
            fg_color=BG_CARD, 
            corner_radius=12, 
            border_width=2, 
            border_color=ACCENT
        )
        settings_frame.pack(fill="x", padx=40, pady=10)
        
        # Input row
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
            placeholder_text="Paste any website URL (e.g. Polo, Amazon, Blogs)..."
        )
        self.url_entry.pack(side="left", fill="x", expand=True)

        # Radio Toggles row
        radio_container = ctk.CTkFrame(settings_frame, fg_color="transparent")
        radio_container.pack(fill="x", padx=20, pady=(10, 20))
        
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

        # ---------------------------------------------------------
        # Primary Execution Hook
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Log Terminal
        # ---------------------------------------------------------
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

    # ==============================================================================
    # TELEMETRY LOGGING
    # ==============================================================================
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

    # ==============================================================================
    # EXECUTION PIPELINE
    # ==============================================================================
    def on_execute_click(self):
        url = self.url_entry.get().strip()
        if not url:
            self.log("ERROR: Target URL cannot be empty. Please provide a valid URL.")
            return
            
        if not url.startswith("http"):
            url = "https://" + url
            
        # Prevent double triggering
        self.exec_btn.configure(text="Scraping Active...", state="disabled")
        self.url_entry.configure(state="disabled")
        
        self.log("Initializing background thread for scraping...")
        
        # Explicit Multi-threading
        scraper_thread = threading.Thread(
            target=self.run_dynamic_scraper, 
            args=(url,), 
            daemon=True
        )
        scraper_thread.start()

    def reset_ui_state(self):
        """Re-enable UI elements post-execution."""
        def _reset():
            self.exec_btn.configure(text="Execute Web Scraping", state="normal")
            self.url_entry.configure(state="normal")
        self.after(0, _reset)

    # ==============================================================================
    # DYNAMIC DATA EXTRACTION LOGIC (3-TIER SYSTEM)
    # ==============================================================================
    def run_dynamic_scraper(self, target_url: str):
        self.log("Launching background headless driver with MAXIMUM stealth...")
        
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")
        
        # Extreme Anti-Bot Evasion Settings (Crucial for Polo / Cloudflare sites)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # Emulate a perfect, real Windows 11 Chrome browser
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
        
        driver = None
        scraped_data = []
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Execute extreme stealth JS scripts to mask Selenium footprint
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.navigator.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                '''
            })
            
            self.log(f"Navigating to {target_url}...")
            driver.set_page_load_timeout(30)
            
            try:
                driver.get(target_url)
            except Exception as e:
                self.log(f"Initial load timeout/error, but proceeding anyway: {e}")
            
            # Simulated Wait & Deep Scroll for Heavy Lazy Loading (Polo / Zara etc)
            self.log("Injecting wait buffers for heavy scripts to render...")
            time.sleep(5) 
            
            self.log("Executing deep page scrolls to trigger all hidden assets...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # Scroll in smaller chunks rather than jumping to bottom
            for i in range(1, 10):
                scroll_pos = (last_height / 10) * i
                driver.execute_script(f"window.scrollTo(0, {scroll_pos});")
                time.sleep(1.5) # Wait for network requests to fire
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height > last_height:
                    last_height = new_height
                    
            self.log("Applying 3-Tier Universal Extraction Architecture...")
            
            # =============================================================
            # TIER 1: ADVANCED E-COMMERCE HEURISTIC
            # =============================================================
            self.log("-> Tier 1: Searching for complex Product Cards (E-Commerce Mode)...")
            
            # Find both actual images and divs with background images (common on Polo/luxury sites)
            media_elements = driver.find_elements(By.XPATH, "//img | //div[contains(@style, 'background-image')]")
            processed_nodes = set()
            
            # Ultra-broad regex: Matches $, ₹, £, €, Rs, OR just plain formatted numbers like "1,299.00"
            currency_regex = re.compile(r'(?:[$₹£€]|Rs\.?|[A-Z]{2,3})?\s*(?:\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:[$₹£€]|Rs\.?|[A-Z]{2,3})?')
            
            for elem in media_elements:
                try:
                    img_url = (
                        elem.get_attribute("data-src") or 
                        elem.get_attribute("data-lazy-src") or 
                        elem.get_attribute("srcset") or 
                        elem.get_attribute("src")
                    )
                    if not img_url and 'background-image' in (elem.get_attribute("style") or ""):
                        style = elem.get_attribute("style")
                        match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
                        if match:
                            img_url = match.group(1)
                            
                    if not img_url or img_url.startswith("data:image"):
                        continue
                        
                    if "," in img_url:
                        img_url = img_url.split(",")[0].strip().split(" ")[0]

                    # Walk up the DOM (up to 10 parent levels to handle deeply nested luxury sites)
                    current_elem = elem
                    card_found = None
                    price_extracted = None
                    
                    for _ in range(10):
                        current_elem = current_elem.find_element(By.XPATH, "..")
                        if current_elem.tag_name in ['body', 'html']:
                            break
                            
                        text_content = current_elem.text
                        if text_content:
                            matches = currency_regex.findall(text_content)
                            # Filter matches that actually look like prices
                            valid_prices = [m for m in matches if any(c in m for c in '$₹£€Rs') or '.' in m or ',' in m]
                            
                            if valid_prices:
                                card_found = current_elem
                                price_extracted = valid_prices[0].strip()
                                break
                                
                    if card_found and card_found.id not in processed_nodes:
                        processed_nodes.add(card_found.id)
                        
                        title = "Unknown Product"
                        headers = card_found.find_elements(By.CSS_SELECTOR, "h1, h2, h3, h4, h5, h6, .title, .product-name")
                        if headers and headers[0].text.strip():
                            title = headers[0].text.strip()
                        else:
                            lines = [line.strip() for line in card_found.text.split('\n') if line.strip() and line.strip() not in price_extracted]
                            if lines:
                                title = max(lines, key=len)
                                
                        link = "No Link"
                        if card_found.tag_name == "a":
                            link = card_found.get_attribute("href") or link
                        else:
                            links = card_found.find_elements(By.TAG_NAME, "a")
                            if links:
                                link = links[0].get_attribute("href") or link
                                
                        scraped_data.append({
                            "Type": "Product Card",
                            "Title_or_Text": title,
                            "Price_or_Data": price_extracted,
                            "URL_Link": link,
                            "Image_URL": img_url
                        })
                except Exception:
                    pass

            # =============================================================
            # TIER 2: GENERIC ARTICLE / LISTING FALLBACK
            # =============================================================
            if not scraped_data:
                self.log("-> Tier 1 yielded 0 results. Activating Tier 2: Generic Article/Listing Extractor...")
                list_items = driver.find_elements(By.CSS_SELECTOR, "article, .post, .item, li, .card")
                for item in list_items:
                    try:
                        text_content = item.text.strip()
                        if len(text_content) > 15: # Has meaningful text
                            link = "No Link"
                            links = item.find_elements(By.TAG_NAME, "a")
                            if links:
                                link = links[0].get_attribute("href") or link
                                
                            scraped_data.append({
                                "Type": "List/Article Item",
                                "Title_or_Text": text_content[:200].replace('\n', ' | '), # truncated for neatness
                                "Price_or_Data": "N/A",
                                "URL_Link": link,
                                "Image_URL": "N/A"
                            })
                    except:
                        pass

            # =============================================================
            # TIER 3: THE "NEVER EMPTY HANDED" ULTIMATE FALLBACK (RAW DUMP)
            # =============================================================
            if not scraped_data:
                self.log("-> Tier 2 yielded 0 results. Activating Tier 3: Universal Link & Text Dump...")
                self.log("-> GUARANTEE: Collecting all accessible links and readable data from the page.")
                
                all_links = driver.find_elements(By.TAG_NAME, "a")
                seen_urls = set()
                
                for a in all_links:
                    try:
                        href = a.get_attribute("href")
                        txt = a.text.strip()
                        if href and href not in seen_urls and href.startswith("http"):
                            seen_urls.add(href)
                            scraped_data.append({
                                "Type": "Raw Hyperlink",
                                "Title_or_Text": txt if txt else "Image/Icon Link",
                                "Price_or_Data": "N/A",
                                "URL_Link": href,
                                "Image_URL": "N/A"
                            })
                    except:
                        pass

            # Final check
            if scraped_data:
                self.log(f"Extraction Pipeline Complete! Successfully forced collection of {len(scraped_data)} records.")
            else:
                self.log("FATAL: Page is entirely blank, fully blocked by extreme CAPTCHA, or contains zero links.")

        except Exception as e:
            self.log(f"CRITICAL ERROR during extraction process: {str(e)}")
            traceback.print_exc()
        finally:
            if driver:
                self.log("Closing headless web driver instance safely...")
                driver.quit()
                
            # Trigger Data Packaging & Export regardless of which tier succeeded
            if scraped_data:
                self.after(0, self.prompt_export, scraped_data)
            else:
                self.reset_ui_state()

    # ==============================================================================
    # EXPORT ARCHITECTURE
    # ==============================================================================
    def prompt_export(self, data: list):
        export_format = self.format_var.get()
        self.log(f"Opening native system save dialog for {export_format} export...")
        
        if export_format == "CSV":
            file_types = [("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
            default_ext = ".csv"
        else:
            file_types = [("JSON Structured", "*.json"), ("All Files", "*.*")]
            default_ext = ".json"
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Scripy_Export_{timestamp}{default_ext}"

        filepath = filedialog.asksaveasfilename(
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
                        
                self.log(f"SUCCESS: Dataset cleanly written to {filepath}")
            except Exception as e:
                self.log(f"ERROR: Failed to save file - {e}")
        else:
            self.log("Export operation cancelled by user.")
            
        self.reset_ui_state()

if __name__ == "__main__":
    app = ScripyApp()
    app.mainloop()
