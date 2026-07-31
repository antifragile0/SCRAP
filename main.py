import requests
import concurrent.futures
import os

# Konfigurasi
SOURCES_FILE = 'sources.txt'
OUTPUT_FILE = 'playlist.m3u'
# Gunakan huruf kecil untuk memudahkan pencocokan (case-insensitive)
TARGET_KEYWORDS = ["nasional", "indonesia"] 
TIMEOUT = 5 # Maksimal waktu tunggu per link (detik)

# Headers disamakan dengan contoh EXT-VLC-OPT Anda agar tidak diblokir server
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0'
}

def get_sources():
    if not os.path.exists(SOURCES_FILE):
        return []
    with open(SOURCES_FILE, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def scrape_m3u(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[!] Gagal mengunduh sumber: {url} | Error: {e}")
        return ""

def parse_and_filter_m3u(content):
    lines = content.splitlines()
    channels = []
    
    current_extinf = ""
    current_extvlcopt = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("#EXTINF"):
            current_extinf = line
        elif line.startswith("#EXTVLCOPT"):
            current_extvlcopt = line
        elif not line.startswith("#"): # Ini adalah baris URL M3U8 / MPD
            url = line
            # Cek apakah EXTINF mengandung keyword target
            extinf_lower = current_extinf.lower()
            if any(keyword in extinf_lower for keyword in TARGET_KEYWORDS):
                channels.append({
                    'extinf': current_extinf,
                    'extvlcopt': current_extvlcopt,
                    'url': url
                })
            
            # Reset untuk channel berikutnya
            current_extinf = ""
            current_extvlcopt = ""
            
    return channels

def check_url_active(channel):
    url = channel['url']
    try:
        # Gunakan stream=True agar hanya mendownload header, bukan keseluruhan video
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        if response.status_code == 200:
            return channel
    except:
        pass
    return None

def main():
    print("[*] Membaca sumber M3U...")
    sources = get_sources()
    
    all_filtered_channels = []
    
    for source in sources:
        print(f"[*] Mengunduh & memfilter: {source}")
        content = scrape_m3u(source)
        channels = parse_and_filter_m3u(content)
        all_filtered_channels.extend(channels)
        
    print(f"[*] Total channel masuk filter nama: {len(all_filtered_channels)}")
    print("[*] Memulai pengecekan URL (menghapus yang mati)...")
    
    active_channels = []
    
    # Gunakan ThreadPoolExecutor untuk mengecek banyak URL secara bersamaan
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(check_url_active, all_filtered_channels)
        
        for result in results:
            if result is not None:
                active_channels.append(result)
                
    print(f"[*] Channel yang aktif: {len(active_channels)}")
    
    # Simpan ke playlist akhir
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for ch in active_channels:
            if ch['extinf']:
                f.write(f"{ch['extinf']}\n")
            if ch['extvlcopt']:
                f.write(f"{ch['extvlcopt']}\n")
            f.write(f"{ch['url']}\n")
            
    print(f"[*] Playlist berhasil disimpan ke {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
