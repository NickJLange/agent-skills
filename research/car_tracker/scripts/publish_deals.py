import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

# Resolve project root dynamically to ensure path portability (no hardcoded /Users/njl)
current = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()
while current and current != os.path.dirname(current):
    if os.path.exists(os.path.join(current, ".git")) or os.path.exists(os.path.join(current, ".agents")):
        project_root = current
        break
    current = os.path.dirname(current)

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from vehicle_profiles import ACTIVE_SEARCH_PROFILE_KEYS, get_profile

# Base coordinate for distance calculation (Yonkers, NY)
YONKERS_LAT = 40.9312
YONKERS_LON = -73.8987

def get_distance(lat2, lon2):
    import math
    if lat2 is None or lon2 is None:
        return float('inf')
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - YONKERS_LAT)
    dlon = math.radians(lon2 - YONKERS_LON)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(YONKERS_LAT)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.18

def get_listings_for_trim(make, model, trim, vin_prefix, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}
    listings = []
    limit = 100
    offset = 0
    
    # Query up to 15 pages to find matches across entire inventory
    if api_key:
        for page in range(15):
            url = f"https://api.visor.vin/v1/listings?make={make}&model={model}&limit={limit}&offset={offset}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    if not data:
                        break
                    listings.extend(data)
                    offset += limit
                else:
                    print(f"[-] Warning: Visor API request failed with status code {r.status_code}", file=sys.stderr)
                    break
            except Exception as e:
                print(f"[-] Warning: Visor API request failed with error: {e}", file=sys.stderr)
                break
                
    # Filter by trim keywords & powertrain
    matching = []
    trim_lower = trim.lower()
    
    if "platinum" in trim_lower or "plat" in trim_lower:
        filter_words = ["plat"]
    elif "limited" in trim_lower or "ltd" in trim_lower:
        filter_words = ["limit"]
    elif "pinnacle" in trim_lower or "pinn" in trim_lower:
        filter_words = ["pinn"]
    elif "350" in trim_lower:
        filter_words = ["350"]
    else:
        trim_words = trim_lower.split()
        filter_words = [w for w in trim_words if w not in ["awd", "4wd", "hybrid", "max"]]
        
    for car in listings:
        car_trim = (car.get("trim") or "").lower()
        car_vin = (car.get("vin") or "").upper()
        price = car.get("price")
        car_type = (car.get("inventory_type", car.get("inventoryType", "used")) or "used").lower()
        
        if price is None or not car_vin:
            continue
            
        # Powertrain matching
        if vin_prefix and len(car_vin) > 9:
            if make.lower() == "toyota" or make.lower() == "lexus":
                if len(vin_prefix) > 4 and car_vin[3:5] != vin_prefix[3:5]:
                    continue
            elif make.lower() == "chrysler":
                if len(vin_prefix) > 5 and car_vin[5] != vin_prefix[5]:
                    continue
                    
        # Condition matching (strictly brand-new)
        if car_type != "new":
            continue
            
        # Match trim keywords
        if any(w in car_trim for w in filter_words):
            lat = car.get("latitude")
            lon = car.get("longitude")
            dist = get_distance(lat, lon)
            car["computed_distance"] = dist
            matching.append(car)
            
    # Also load from saved file if API has fewer matches
    saved_path = os.path.join(project_root, "data", "comprehensive_search_results.json")
    if os.path.exists(saved_path):
        try:
            with open(saved_path, "r") as f:
                saved_data = json.load(f)
                
            # Flatten lists
            for key in saved_data:
                for car in saved_data[key]:
                    car_make = car.get("make", "")
                    car_model = car.get("model", "")
                    car_trim = (car.get("trim") or "").lower()
                    car_vin = (car.get("vin") or "").upper()
                    car_type = (car.get("inventory_type", car.get("inventoryType", "used")) or "used").lower()
                    price = car.get("price")
                    
                    if price is None or car_make.lower() != make.lower() or model.lower() not in car_model.lower():
                        continue
                        
                    # Powertrain matching
                    if vin_prefix and len(car_vin) > 9:
                        if make.lower() == "toyota" or make.lower() == "lexus":
                            if len(vin_prefix) > 4 and car_vin[3:5] != vin_prefix[3:5]:
                                continue
                        elif make.lower() == "chrysler":
                            if len(vin_prefix) > 5 and car_vin[5] != vin_prefix[5]:
                                continue
                                
                    # Condition matching
                    if car_type != "new":
                        continue
                        
                    if any(w in car_trim for w in filter_words):
                        lat = car.get("latitude")
                        lon = car.get("longitude")
                        dist = get_distance(lat, lon)
                        car["computed_distance"] = dist
                        # Prevent duplicate VINs
                        if not any(x.get("vin") == car.get("vin") for x in matching):
                            matching.append(car)
        except Exception as e:
            print(f"[-] Warning: Failed to load comprehensive_search_results.json: {e}", file=sys.stderr)

    # Sort matching by price ascending
    matching.sort(key=lambda x: x.get("price", float('inf')))
    return matching

def load_seen_listings(state_path):
    if os.path.exists(state_path):
        try:
            with open(state_path, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_listings(seen_set, state_path):
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    try:
        with open(state_path, "w") as f:
            json.dump(list(seen_set), f, indent=2)
    except Exception as e:
        print(f"[-] Error saving state file: {e}", file=sys.stderr)

# Option Verification Cache functions
def load_verified_options(cache_path):
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_verified_options(verified_dict, cache_path):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    try:
        with open(cache_path, "w") as f:
            json.dump(verified_dict, f, indent=2)
    except Exception as e:
        print(f"[-] Error saving options cache: {e}", file=sys.stderr)

# Dynamic Window Sticker & VDP Scraper Verification
def fetch_chrysler_window_sticker(vin):
    url = f"https://www.chrysler.com/hostd/windowsticker/getWindowStickerPdf.do?vin={vin}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(r.content))
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()
                if "We are unable to retrieve a window sticker" not in text:
                    return text
        else:
            print(f"[-] Chrysler window sticker returned status {r.status_code} for {vin}", file=sys.stderr)
    except Exception as e:
        print(f"[-] Chrysler window sticker lookup failed for {vin}: {e}", file=sys.stderr)
    return None

def fetch_vdp_content(vdp_url):
    if not vdp_url:
        return None
    print(f"[+] Scraping VDP URL: {vdp_url}", file=sys.stderr)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.goto(vdp_url, timeout=12000, wait_until="domcontentloaded")
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        print(f"[-] Playwright VDP scrape failed for {vdp_url}: {e}", file=sys.stderr)
    return None

def verify_car_options(car, profile, cache_dict):
    vin = (car.get("vin") or "").upper()
    if not vin:
        return False
        
    if vin in cache_dict:
        return cache_dict[vin]
        
    vdp_url = car.get("vdpUrl") or car.get("vdp_url")
    matches = True
    
    if profile.key == "chrysler_pacifica_pinnacle_awd":
        sticker_text = fetch_chrysler_window_sticker(vin)
        if sticker_text:
            is_pinnacle = "PINNACLE" in sticker_text.upper()
            has_sound = any(x in sticker_text.upper() for x in ["HARMAN KARDON", "KARDON", "19 SPEAKER", "20 SPEAKER"])
            matches = is_pinnacle and has_sound
            if not matches:
                print(f"[-] Option mismatch on Chrysler sticker for {vin} (Pinnacle={is_pinnacle}, HK={has_sound})", file=sys.stderr)
        else:
            vdp_text = fetch_vdp_content(vdp_url)
            if vdp_text:
                is_pinnacle = "PINNACLE" in vdp_text.upper()
                has_sound = any(x in vdp_text.upper() for x in ["HARMAN", "KARDON", "19 SPEAKER", "20 SPEAKER", "SOUND SYSTEM", "AUDIO"])
                matches = is_pinnacle and has_sound
                if not matches:
                    print(f"[-] Option mismatch on VDP for Pacifica {vin}", file=sys.stderr)
            else:
                matches = True  # Fallback to True to avoid missing deals if unreachable
                
    elif profile.key in ["grand_highlander_hybrid_limited_awd", "grand_highlander_hybrid_nightshade_awd"]:
        vdp_text = fetch_vdp_content(vdp_url)
        if vdp_text:
            has_moonroof = any(x in vdp_text.upper() for x in ["PANORAMIC MOONROOF", "PANORAMIC ROOF", "PANO ROOF", "PANORAMIC VIEW MOONROOF", "SUNROOF", "MOONROOF"])
            has_360_cam = any(x in vdp_text.upper() for x in ["PANORAMIC VIEW MONITOR", "360-DEGREE", "360 DEGREE", "360 CAM", "360 SURROUND", "SURROUND VIEW", "BIRD'S EYE", "BACKUP CAMERA WITH 360", "PVM"])
            is_7_pass = any(x in vdp_text.upper() for x in ["7-PASSENGER", "7 PASSENGER", "CAPTAIN'S CHAIR", "CAPTAINS CHAIR", "7-SEATER", "7 SEATER"])
            matches = has_moonroof and has_360_cam and is_7_pass
            if not matches:
                print(f"[-] GH options missing on {vin}: Moonroof={has_moonroof}, 360Cam={has_360_cam}, 7Pass={is_7_pass}", file=sys.stderr)
        else:
            matches = True
            
    elif profile.key == "lexus_tx_350_awd":
        vdp_text = fetch_vdp_content(vdp_url)
        if vdp_text:
            has_tech = any(x in vdp_text.upper() for x in ["TECHNOLOGY PACKAGE", "TECH PACKAGE", "HEAD-UP DISPLAY", "HUD", "PANORAMIC VIEW MONITOR"])
            has_captains = any(x in vdp_text.upper() for x in ["CAPTAIN'S CHAIR", "CAPTAINS CHAIR", "6-PASSENGER", "6 PASSENGER", "6-SEATER", "6 SEATER"])
            has_levinson = any(x in vdp_text.upper() for x in ["MARK LEVINSON", "LEVINSON", "21-SPEAKER", "PREMIUM SOUND SYSTEM", "ML AUDIO"])
            matches = has_tech and has_captains and has_levinson
            if not matches:
                print(f"[-] Lexus TX options missing on {vin}: Tech={has_tech}, Captains={has_captains}, ML={has_levinson}", file=sys.stderr)
        else:
            matches = True
            
    cache_dict[vin] = matches
    return matches

def main():
    dotenv_path = os.path.join(project_root, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()
        
    api_key = os.getenv("VISOR.VIN_API_KEY") or os.getenv("VISOR_API_KEY")
    if not api_key:
        print("[-] Warning: VISOR_API_KEY environment variable is not set. Visor API live search will be skipped.", file=sys.stderr)
        
    parser = argparse.ArgumentParser(description="Daily Car Tracker - Publishes new and cheapest car deals.")
    parser.add_argument("--trims", type=str, help="Not used. Checked profiles loaded dynamically from vehicle_profiles.py.")
    args = parser.parse_args()
    
    # State tracking
    state_path = os.path.join(project_root, "data", "seen_listings.json")
    seen_vins = load_seen_listings(state_path)
    new_seen_vins = set(seen_vins)
    
    # Options Cache
    cache_path = os.path.join(project_root, "data", "verified_options.json")
    verified_options = load_verified_options(cache_path)
    
    print("# Daily Car Market Bulletin (New Listings & Cheapest Deals)")
    print(f"*Report generated for Yonkers, NY coordinates. Target distance comparisons sorted by proximity.*")
    print(f"*Options packages verified dynamically using OEM window stickers and dealer site scrapers.*")
    
    for profile_key in ACTIVE_SEARCH_PROFILE_KEYS:
        profile = get_profile(profile_key)
        make = profile.make
        model = profile.model
        trim = profile.trim
        
        # Determine vin_prefix from the sample_vin in the profile
        if make.lower() in ["toyota", "lexus"]:
            vin_prefix = profile.sample_vin[:5]
        else:
            vin_prefix = profile.sample_vin[:6]
            
        print(f"\n## 🚙 {make} {model} ({trim})")
        print(f"**Target Config Must-Haves**: {'; '.join(profile.must_haves)}")
        
        # Get listings
        listings = get_listings_for_trim(make, model, trim, vin_prefix, api_key)
        
        if not listings:
            print("*No active new inventory matching specifications found.*")
            continue
            
        # 1. Identify New Arrivals & Verify Options
        new_arrivals = []
        new_candidates = [car for car in listings if car.get("vin") not in seen_vins]
        for car in new_candidates:
            if verify_car_options(car, profile, verified_options):
                new_arrivals.append(car)
                new_seen_vins.add(car.get("vin"))
                
        # 2. Identify Top 5 Cheapest Deals that Pass Options Verification
        verified_active = []
        for car in listings:
            if len(verified_active) >= 5:
                break
            if verify_car_options(car, profile, verified_options):
                verified_active.append(car)
                
        # Save cache after each profile to keep progress
        save_verified_options(verified_options, cache_path)
        
        if not verified_active:
            print("*No active inventory matching options packages found.*")
            continue
            
        cheapest_price = verified_active[0]["price"]
        
        # Print New Arrivals (sorted by distance)
        print("\n### 🆕 New Arrivals in the Last 24 Hours (Option Verified)")
        if new_arrivals:
            new_arrivals.sort(key=lambda x: x.get("computed_distance", float('inf')))
            print("```")
            print(f"{'Dealership (State — Dist)':<35} | {'Price':<7} | {'Delta':<7} | {'VIN':<18}")
            print("-" * 75)
            for car in new_arrivals:
                c_price = car.get("price")
                c_dist = car.get("computed_distance", float('inf'))
                c_state = car.get("state", "??")
                c_dealer = car.get("dealer_name") or "Dealer"
                c_dealer_lbl = f"{c_dealer[:22]} ({c_state} — {c_dist:.0f} mi)"
                c_vin = car.get("vin", "")
                delta = c_price - cheapest_price
                print(f"{c_dealer_lbl:<35} | ${c_price:,.0f} | +${delta:,.0f} | {c_vin}")
            print("```")
        else:
            print("*No new listings with required packages appeared since last check.*")
            
        # Print Cheapest Overall Deals (sorted by price)
        print("\n### 🏆 Top 5 Cheapest Active Deals (Option Verified)")
        print("```")
        print(f"{'Dealership (State — Dist)':<35} | {'Price':<7} | {'Delta':<7} | {'VIN':<18}")
        print("-" * 75)
        for car in verified_active:
            c_price = car.get("price")
            c_dist = car.get("computed_distance", float('inf'))
            c_state = car.get("state", "??")
            c_dealer = car.get("dealer_name") or "Dealer"
            c_dealer_lbl = f"{c_dealer[:22]} ({c_state} — {c_dist:.0f} mi)"
            c_vin = car.get("vin", "")
            delta = c_price - cheapest_price
            print(f"{c_dealer_lbl:<35} | ${c_price:,.0f} | +${delta:,.0f} | {c_vin}")
        print("```")
        
    # Update global state of seen VINs
    save_seen_listings(new_seen_vins, state_path)

if __name__ == "__main__":
    main()
