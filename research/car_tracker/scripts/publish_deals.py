import os
import sys
import json
import argparse
import requests
import time
from dotenv import load_dotenv

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

def extract_color(car):
    """Best-effort extraction of paint color from the listing VDP URL and details."""
    text = (car.get("vdp_url") or car.get("vdpUrl") or "").lower()
    trim = (car.get("trim") or "").lower()
    
    color_map = {
        "wind chill": "Wind Chill Pearl",
        "wind-chill": "Wind Chill Pearl",
        "cloudburst": "Cloudburst Gray",
        "caviar": "Caviar Black",
        "eminent white": "Eminent White Pearl",
        "eminent-white": "Eminent White Pearl",
        "nightshade": "Midnight Black (Nightshade)",
        "blueprint": "Blueprint Blue",
        "supersonic red": "Supersonic Red",
        "supersonic-red": "Supersonic Red",
        "velvet red": "Velvet Red Pearl",
        "velvet-red": "Velvet Red Pearl",
        "fathom blue": "Fathom Blue Pearl",
        "fathom-blue": "Fathom Blue Pearl",
        "bright white": "Bright White Clearcoat",
        "bright-white": "Bright White Clearcoat",
        "granite crystal": "Granite Crystal Metallic",
        "granite-crystal": "Granite Crystal Metallic",
        "storm cloud": "Storm Cloud Gray",
        "storm-cloud": "Storm Cloud Gray",
        "silver sterling": "Silver Sterling Metallic",
        "silver-sterling": "Silver Sterling Metallic",
        "celestial silver": "Celestial Silver Metallic",
        "celestial-silver": "Celestial Silver Metallic",
        "midnight black": "Midnight Black Metallic",
        "midnight-black": "Midnight Black Metallic",
        "supersonic": "Supersonic Red",
        "supersonicred": "Supersonic Red",
        "white": "White",
        "black": "Black",
        "gray": "Gray",
        "grey": "Gray",
        "silver": "Silver",
        "blue": "Blue",
        "red": "Red",
        "bronze": "Bronze",
    }
    
    for key, val in color_map.items():
        if key in text or key in trim:
            return val
            
    return "TBD"

# Global cache for listing details
details_cache = {}

def seed_details_cache(project_root):
    # Try seeding from national discount analysis first to avoid hitting API rate limits
    paths = [
        os.path.join(project_root, "national_discount_analysis.json"),
        os.path.join(project_root, "data", "national_discount_analysis.json"),
        "national_discount_analysis.json"
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for key, cars in data.items():
                        for car in cars:
                            vin = car.get("vin")
                            if vin:
                                details_cache[vin] = {
                                    "vehicle": {
                                        "build": {
                                            "exterior_color": car.get("exteriorColor") or car.get("exterior_color"),
                                            "combined_msrp": car.get("msrp") or car.get("reference_msrp")
                                        }
                                    }
                                }
                                if car.get("id"):
                                    details_cache[car.get("id")] = details_cache[vin]
                print(f"[+] Loaded/Seeded details cache from {path}", file=sys.stderr)
                break
            except Exception as e:
                print(f"[-] Warning: Failed to seed details cache from {path}: {e}", file=sys.stderr)

def get_color_and_options(car, api_key):
    listing_id = car.get("id")
    vin = car.get("vin")
    
    # Try ID or VIN lookup in cache
    details = None
    if listing_id and listing_id in details_cache:
        details = details_cache[listing_id]
    elif vin and vin in details_cache:
        details = details_cache[vin]
        
    if details is None and listing_id and api_key:
        url = f"https://api.visor.vin/v1/listings/{listing_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                details = r.json().get("data", {})
                details_cache[listing_id] = details
                if vin:
                    details_cache[vin] = details
                time.sleep(0.5)  # small rate-limit spacing
            else:
                details = {}
        except Exception:
            details = {}
            
    if details:
        vehicle = details.get("vehicle", {})
        build = vehicle.get("build", {})
        color = build.get("exterior_color")
        if color:
            return color
            
    return extract_color(car)

def get_msrp_info(car, api_key):
    listing_id = car.get("id")
    vin = car.get("vin")
    
    # Ensure color/options fetching has populated cache
    get_color_and_options(car, api_key)
    
    details = None
    if listing_id and listing_id in details_cache:
        details = details_cache[listing_id]
    elif vin and vin in details_cache:
        details = details_cache[vin]
        
    if details:
        # Check vehicle build combined_msrp
        vehicle = details.get("vehicle", {})
        build = vehicle.get("build", {})
        msrp = build.get("combined_msrp") or build.get("base_msrp")
        if msrp:
            return msrp
        # Check pricing line_items
        pricing = details.get("pricing", {})
        if pricing:
            for item in pricing.get("line_items", []):
                if item.get("role") == "pricing_anchor" or item.get("subtype") == "msrp":
                    return item.get("amount_usd")
    return None

def car_matches_profile(car, make, model, trim, vin_prefix, req_keywords, requires_awd, requires_hybrid):
    car_trim = (car.get("trim") or "").lower()
    car_vin = (car.get("vin") or "").upper()
    price = car.get("price")
    car_type = (car.get("inventory_type", car.get("inventoryType", "used")) or "used").lower()
    
    if price is None or not car_vin:
        return False
        
    # Powertrain matching
    if vin_prefix and len(car_vin) > 9:
        if make.lower() == "toyota" or make.lower() == "lexus":
            if len(vin_prefix) > 4 and car_vin[3:5] != vin_prefix[3:5]:
                return False
        elif make.lower() == "chrysler":
            if len(vin_prefix) > 5 and car_vin[5] != vin_prefix[5]:
                return False
                
    # Condition matching (strictly new)
    if car_type != "new":
        return False
        
    # Match trim keywords
    listing_text = f"{model} {car_trim}".upper()
    if req_keywords:
        if not any(k.upper() in listing_text for k in req_keywords):
            return False
            
    # Match AWD
    if requires_awd:
        is_awd_flag = car.get("is_awd") or (car.get("drivetrain") or "").upper() in ("AWD", "4WD", "4X4", "ALL-WHEEL DRIVE")
        if not is_awd_flag:
            vdp_url = car.get("vdp_url") or car.get("vdpUrl") or ""
            awd_text = f"{model} {car_trim} {vdp_url}".upper()
            is_awd_flag = any(token in awd_text for token in ("AWD", "4WD", "4X4"))
        if not is_awd_flag and len(car_vin) > 6:
            if car_vin.startswith(("5TDAA", "5TDAC", "5TDAD")):
                is_awd_flag = (car_vin[6] == "B")
        if not is_awd_flag:
            return False
            
    # Match Hybrid
    if requires_hybrid:
        hybrid_text = f"{model} {car_trim}".upper()
        is_hybrid_flag = "HYBRID" in hybrid_text or car_vin.startswith(("5TDAC", "5TDAD"))
        if not is_hybrid_flag:
            return False
            
    return True

def get_listings_for_trim(target, api_key, project_root):
    make = target["make"]
    model = target["model"]
    trim = target["trim"]
    vin_prefix = target.get("vin_prefix") or target.get("sample_vin")
    
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
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
                    time.sleep(1.0) # sleep 1.0s between pages to stay under rate limits
                else:
                    print(f"[-] Warning: Visor API request failed with status code {r.status_code}", file=sys.stderr)
                    break
            except Exception as e:
                print(f"[-] Warning: Visor API request failed with error: {e}", file=sys.stderr)
                break
                
    # Filter by trim keywords, AWD, Hybrid, and powertrain prefix
    matching = []
    
    # Extract criteria from target configuration
    req_keywords = target.get("required_trim_keywords")
    if req_keywords is None:
        trim_lower = trim.lower()
        if "platinum" in trim_lower or "plat" in trim_lower:
            req_keywords = ["plat"]
        elif "limited" in trim_lower or "ltd" in trim_lower:
            req_keywords = ["limit"]
        elif "pinnacle" in trim_lower or "pinn" in trim_lower:
            req_keywords = ["pinn"]
        elif "350" in trim_lower:
            req_keywords = ["350"]
        else:
            trim_words = trim_lower.split()
            req_keywords = [w for w in trim_words if w not in ["awd", "4wd", "hybrid", "max"]]
            
    requires_awd = target.get("requires_awd")
    if requires_awd is None:
        requires_awd = "awd" in trim.lower() or "4wd" in trim.lower() or "4x4" in trim.lower()
        
    requires_hybrid = target.get("requires_hybrid")
    if requires_hybrid is None:
        requires_hybrid = "hybrid" in trim.lower()
        
    for car in listings:
        if car_matches_profile(car, make, model, trim, vin_prefix, req_keywords, requires_awd, requires_hybrid):
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
                
            # Flatten lists and search under all keys
            for key in saved_data:
                for car in saved_data[key]:
                    car_make = car.get("make", "")
                    car_model = car.get("model", "")
                    
                    if car_make.lower() != make.lower() or model.lower() not in car_model.lower():
                        continue
                        
                    if car_matches_profile(car, make, model, trim, vin_prefix, req_keywords, requires_awd, requires_hybrid):
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

def main():
    # Resolve project root dynamically to ensure path portability
    current = os.path.dirname(os.path.abspath(__file__))
    project_root = os.getcwd()
    while current and current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, ".git")) or os.path.exists(os.path.join(current, ".agents")):
            project_root = current
            break
        current = os.path.dirname(current)

    dotenv_path = os.path.join(project_root, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    else:
        load_dotenv()
        
    # Seed our details cache from national discount analysis JSON
    seed_details_cache(project_root)
        
    api_key = os.getenv("VISOR.VIN_API_KEY") or os.getenv("VISOR_API_KEY")
    if not api_key:
        print("[-] Warning: VISOR_API_KEY environment variable is not set. Visor API live search will be skipped.", file=sys.stderr)
        
    parser = argparse.ArgumentParser(description="Daily Car Tracker - Publishes new and cheapest car deals.")
    parser.add_argument("--trims", type=str, help="Path to JSON config of trims to monitor")
    args = parser.parse_args()
    
    # Load monitored trims/profiles from configuration file
    trims_path = args.trims
    if not trims_path:
        for loc in [
            os.path.join(project_root, "config", "target_profiles.json"),
            os.path.join(project_root, "data", "target_profiles.json"),
            os.path.join(project_root, "target_profiles.json"),
            os.path.join(project_root, "data", "tracked_trims.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_profiles.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target_profiles.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "target_profiles.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tracked_trims.json")
        ]:
            if os.path.exists(loc):
                trims_path = loc
                break
                
    if not trims_path or not os.path.exists(trims_path):
        print("[-] Error: Configuration file not found. Please create 'config/target_profiles.json' or supply --trims.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with open(trims_path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # Convert profile dict to list of profile targets
                monitored_trims = list(data.values())
            else:
                monitored_trims = data
    except Exception as e:
        print(f"[-] Error loading config from {trims_path}: {e}", file=sys.stderr)
        sys.exit(1)
        
    # State tracking
    state_path = os.path.join(project_root, "data", "seen_listings.json")
    seen_vins = load_seen_listings(state_path)
    new_seen_vins = set(seen_vins)
    
    print("# Daily Car Market Bulletin (New Listings & Cheapest Deals)")
    print(f"*Report generated for Yonkers, NY coordinates. Target distance comparisons sorted by proximity.*")
    
    first = True
    for target in monitored_trims:
        if not first:
            time.sleep(2.0)
        first = False
        
        make = target["make"]
        model = target["model"]
        trim = target["trim"]
        
        print(f"\n## 🚙 {make} {model} ({trim})")
        
        # Get listings
        listings = get_listings_for_trim(target, api_key, project_root)
        
        if not listings:
            print("*No active new inventory matching specifications found.*")
            continue
            
        cheapest_price = listings[0]["price"]
        
        # 1. Identify New Arrivals
        new_arrivals = []
        for car in listings:
            vin = car.get("vin")
            if vin not in seen_vins:
                new_arrivals.append(car)
                new_seen_vins.add(vin)
                
        # Print New Arrivals (sorted by distance)
        print("\n### 🆕 New Arrivals in the Last 24 Hours")
        if new_arrivals:
            new_arrivals.sort(key=lambda x: x.get("computed_distance", float('inf')))
            print(f"| {'Dealership (State — Dist)':<35} | {'Price (% off MSRP)':<20} | {'Delta':<7} | {'Color':<18} | {'VIN':<18} | {'Visor Link':<12} | {'Dealer Site':<12} |")
            print(f"| {'-' * 35} | {'-' * 20} | {'-' * 7} | {'-' * 18} | {'-' * 18} | {'-' * 12} | {'-' * 12} |")
            for car in new_arrivals:
                c_price = car.get("price")
                c_dist = car.get("computed_distance", float('inf'))
                c_state = car.get("state", "??")
                c_dealer = car.get("dealer_name") or "Dealer"
                c_dealer_lbl = f"{c_dealer[:22]} ({c_state} — {c_dist:.0f} mi)"
                c_vin = car.get("vin", "")
                delta = c_price - cheapest_price
                c_vdp = car.get("vdp_url") or car.get("vdpUrl") or "#"
                c_color = get_color_and_options(car, api_key)
                c_msrp = get_msrp_info(car, api_key)
                if c_msrp and c_msrp > 0:
                    discount = c_msrp - c_price
                    pct_off = (discount / c_msrp) * 100
                    if pct_off >= 0:
                        price_lbl = f"${c_price:,.0f} (-{pct_off:.1f}%)"
                    else:
                        price_lbl = f"${c_price:,.0f} (+{abs(pct_off):.1f}%)"
                else:
                    price_lbl = f"${c_price:,.0f}"
                visor_str = f"[Visor](https://visor.vin/search/listings/{c_vin})" if c_vin else "N/A"
                link_str = f"[Dealer Site]({c_vdp})" if c_vdp != "#" else "N/A"
                print(f"| {c_dealer_lbl:<35} | {price_lbl:<20} | +${delta:,.0f} | {c_color:<18} | {c_vin} | {visor_str} | {link_str} |")
        else:
            print("*No new listings appeared on the market since last check.*")
            
        # Print Cheapest Overall Deals (sorted by price)
        print("\n### 🏆 Top 5 Cheapest Active Deals")
        top_cheapest = listings[:5]
        print(f"| {'Dealership (State — Dist)':<35} | {'Price (% off MSRP)':<20} | {'Delta':<7} | {'Color':<18} | {'VIN':<18} | {'Visor Link':<12} | {'Dealer Site':<12} |")
        print(f"| {'-' * 35} | {'-' * 20} | {'-' * 7} | {'-' * 18} | {'-' * 18} | {'-' * 12} | {'-' * 12} |")
        for car in top_cheapest:
            c_price = car.get("price")
            c_dist = car.get("computed_distance", float('inf'))
            c_state = car.get("state", "??")
            c_dealer = car.get("dealer_name") or "Dealer"
            c_dealer_lbl = f"{c_dealer[:22]} ({c_state} — {c_dist:.0f} mi)"
            c_vin = car.get("vin", "")
            delta = c_price - cheapest_price
            c_vdp = car.get("vdp_url") or car.get("vdpUrl") or "#"
            c_color = get_color_and_options(car, api_key)
            c_msrp = get_msrp_info(car, api_key)
            if c_msrp and c_msrp > 0:
                discount = c_msrp - c_price
                pct_off = (discount / c_msrp) * 100
                if pct_off >= 0:
                    price_lbl = f"${c_price:,.0f} (-{pct_off:.1f}%)"
                else:
                    price_lbl = f"${c_price:,.0f} (+{abs(pct_off):.1f}%)"
            else:
                price_lbl = f"${c_price:,.0f}"
            visor_str = f"[Visor](https://visor.vin/search/listings/{c_vin})" if c_vin else "N/A"
            link_str = f"[Dealer Site]({c_vdp})" if c_vdp != "#" else "N/A"
            print(f"| {c_dealer_lbl:<35} | {price_lbl:<20} | +${delta:,.0f} | {c_color:<18} | {c_vin} | {visor_str} | {link_str} |")
        
    # Update global state of seen VINs
    save_seen_listings(new_seen_vins, state_path)

if __name__ == "__main__":
    main()
