"""
TRT Yayın Akışı (EPG) verisini çeken script.

Nasıl çalışır:
1. https://www.trt.net.tr/yayin-akisi sayfasının HTML'ini indirir.
2. Sayfa içine gömülü `window.__NUXT__=(function(...){...})(...)` script'ini bulur.
   (Bu, Nuxt.js'in server-side render ettiği veriyi taşıyan minify edilmiş bir
   fonksiyon çağrısıdır — düz JSON değildir, bu yüzden regex ile çekilemez.)
3. Bu script'i Node.js ile, sahte bir `window` objesi vererek çalıştırır (eval).
4. window.__NUXT__.data[0].streamEpg altındaki veriyi JSON olarak kaydeder.

Gereksinimler:
- Python 3
- Node.js (sistemde kurulu olmalı, `node --version` ile kontrol edebilirsin)
- requests (`pip install requests`)

Kullanım:
    python3 trt_epg_cek.py
"""

import json
import re
import subprocess
import sys
import tempfile
import os

import requests

URL = "https://www.trt.net.tr/yayin-akisi"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def sayfa_indir() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def nuxt_script_cikar(html: str) -> str:
    idx = html.find("__NUXT__=")
    if idx == -1:
        raise RuntimeError("HTML içinde '__NUXT__=' bulunamadı.")

    start = html.rfind("<script", 0, idx)
    end = html.find("</script>", idx)
    if start == -1 or end == -1:
        raise RuntimeError("__NUXT__ script tag'i sınırları bulunamadı.")
    script_tag = html[start:end]
    # açılış <script ...> tag'ini at, sadece JS içeriğini bırak
    script_content = script_tag[script_tag.find(">") + 1 :]
    return script_content


def node_ile_calistir(script_content: str) -> dict:
    """Script'i Node.js'de sahte bir window objesiyle çalıştırıp
    window.__NUXT__'ı JSON olarak döndürür."""
    # işletim sisteminde geçici bir klasör oluştururmak için with bloğu bitince otomatik siler. 
    # Neden lazım? Çünkü Node'a vereceğimiz .js dosyalarını bir yere yazmamız lazım, ama iş bitince ortalıkta çöp bırakmak istemiyoruz.
    # tmp değişkeni, o klasörün yolunu (path) tutuyor.
    with tempfile.TemporaryDirectory() as tmp:
        js_path = os.path.join(tmp, "nuxt_script.js")
        runner_path = os.path.join(tmp, "runner.js")
        out_path = os.path.join(tmp, "out.json")

        with open(js_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        runner_code = f"""
const fs = require('fs');
const script = fs.readFileSync({js_path!r}, 'utf-8');
const window = {{}};
try {{
  eval(script);
  fs.writeFileSync({out_path!r}, JSON.stringify(window.__NUXT__));
  console.log('OK');
}} catch (e) {{
  console.error('ERROR: ' + e.message);
  process.exit(1);
}}
"""
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(runner_code)

        result = subprocess.run(
            ["node", runner_path], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node.js hata verdi: {result.stderr.strip()}")

        with open(out_path, encoding="utf-8") as f:
            return json.load(f)


def main():
    print("Sayfa indiriliyor HTML olarak")
    html = sayfa_indir()
    print(f"  -> {len(html)} karakter indirildi.")

    print("NUXT script'i çıkarılıyor, kodu tekrar çalıştırabilmek için.")
    script_content = nuxt_script_cikar(html)
    print(f"  -> {len(script_content)} karakter script bulundu.")

    print("Node.js ile çalıştırılıyor (JS evaluate)...")
    nuxt_data = node_ile_calistir(script_content)
    print("  -> Başarılı.")

    stream_epg = nuxt_data["data"][0]["streamEpg"]

    out_file = "trt_epg.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(stream_epg, f, ensure_ascii=False, indent=2)

    print(f"\nKaydedildi: {out_file}")
    print(f"Toplam gün sayısı: {len(stream_epg)}")

    # Örnek: ilk günün ilk kanalının ilk 3 programını göster
    ilk_gun = stream_epg[0]["epgData"][0]
    ilk_kanal = ilk_gun["tvChannels"][0]
    print(f"\nÖrnek -> {ilk_kanal['title']} program of the first day (1.gün):")
    for p in ilk_kanal["past"][:]:
        print(f"  {p['starttime']} -> {p['endtime']} : {p['title']}")
    

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"HATA: {e}", file=sys.stderr)
        sys.exit(1)