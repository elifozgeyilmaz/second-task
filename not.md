# TRT Yayın Akışı Verisini Çekme — Notlar

## Tek cümlede olay

TRT'nin sayfası, veriyi JSON olarak değil, **çalıştırılması gereken bir JavaScript kod parçası** olarak HTML'in içine gizlemiş. Biz de o kodu gerçekten çalıştırıp içinden veriyi çıkardık.

## Üç sayfa sunma modeli (görsel)

![Sayfa sunma modelleri](./Ekran%20Resmi%202026-08-11%2011.54.17.png)

1. **Klasik backend render**: Sunucu hazır HTML üretir, tarayıcı direkt gösterir. Veri HTML içinde düz görünür.
2. **CSR (Client Side Rendering)**: Sunucu boş HTML + JS gönderir, tarayıcıda JS çalışıp ayrı bir API isteği (`fetch`/`xhr`) atar. Network sekmesinde bu istek görünür, API'yi bulmak kolaydır.
3. **SSR + Hydration (TRT'nin / Nuxt'ın yaptığı)**: Backend veriyi önceden çeker, HTML içine bir `<script>window.__NUXT__=...</script>` olarak gömer. Ayrı bir XHR isteği YOK — veri baştan HTML'e gömülü. Tarayıcı bu script'i çalıştırıp sayfayı "canlandırır" (hydration). **Biz de tam bunu yaptık**: script'i çıkarıp Node ile çalıştırdık, içindeki veriyi aldık.

## Somut örnek

Normal bir API olsaydı:
```
GET /api/yayin-akisi
→ {"program": "Haber Bülteni", "saat": "20:00"}
```
Python'da `requests.get(url).json()` yazar, biter.

Ama TRT'nin HTML'i içinde şu var (basitleştirilmiş):
```js
<script>
window.__NUXT__ = (function(a, b) {
  return {"program": a, "saat": b};
})("Haber Bülteni", "20:00");
</script>
```

Bu **JSON değil**, bir **fonksiyon çağrısı**. `a`, `b` gibi kısa parametre isimleri, tekrar eden uzun string'leri (örn. `"false"` gibi 500 kere geçen bir kelime) her seferinde yazmamak için kullanılıyor — sadece dosya boyutunu küçültmek amaçlı bir sıkıştırma tekniği.

## Python neden bunu okuyamıyor

Python `{...}` görünce JSON sanıp okuyabilir. Ama `(function(a,b){...})(...)` bir **program**dır, veri değil. JSON parser bunu anlamaz çünkü bu kod, çalıştırılması gerekiyor.

## Nasıl "çalıştırdık" — adım adım (`veri.py`)

1. **`sayfa_indir()`** → `requests` ile `https://www.trt.net.tr/yayin-akisi` sayfasının HTML'ini indirir (bkz. `veri-cek.py`, çıktı: `sayfa.html`).
2. **`nuxt_script_cikar()`** → HTML içinde `__NUXT__=` ifadesini arar, o script tag'inin başlangıç/bitişini bulup sadece JS kodunu (fonksiyon çağrısını) string olarak çıkarır.
3. **`node_ile_calistir()`** → Bu adım en kritik olanı:
   - Çıkarılan JS kodunu geçici bir `.js` dosyasına yazar.
   - Ayrı bir "runner" script yazar: bu script sahte bir `const window = {}` tanımlar, sonra `eval(script)` ile kodu gerçekten çalıştırır.
   - Kod çalışınca `window.__NUXT__` içine veri dolar (aynı tarayıcıda olduğu gibi).
   - Sonucu `JSON.stringify` ile diske yazar, Python bu dosyayı okuyup geri döndürür.
4. Node.js **çocuk süreç (subprocess)** olarak çağrılıyor — Python kendisi JS çalıştıramaz, bu yüzden gerçek bir JS motoruna (Node) ihtiyaç var.
5. `nuxt_data["data"][0]["streamEpg"]` yolunda asıl aradığımız yayın akışı verisi bulunuyor, bu da `trt_epg.json` olarak kaydediliyor.

## `window` nesnesi neden lazımdı

Kod `window.__NUXT__ = ...` diyor, yani `window` diye bir şeyin **zaten var olduğunu varsayıyor**. Tarayıcıda `window` otomatik var (sayfa objesi). Node.js'de yok — bu yüzden elle `const window = {}` diye boş bir kutu tanımladık, kod çalışınca o kutunun içine veri yazıldı, biz de kutuyu (`window.__NUXT__`) açıp içine baktık.

## Özet akış

```
sayfa.html indir
   → içinden __NUXT__ script'ini kes
   → Node.js'e sahte window ile ver, eval et
   → window.__NUXT__ objesini JSON'a çevir
   → trt_epg.json olarak kaydet
   → Python ile oku
```

## Dosyalar

- `veri-cek.py` — sadece ham HTML'i indirip `sayfa.html`'e kaydeder (ilk deneme / debug amaçlı).
- `veri.py` — asıl script: indirme + script çıkarma + Node ile çalıştırma + `trt_epg.json` üretme.
- `sayfa.html` — TRT'den indirilen ham sayfa.
- `trt_epg.json` — çıkarılan yayın akışı verisi.
