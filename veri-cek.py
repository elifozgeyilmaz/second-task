import requests

url = "https://www.trt.net.tr/yayin-akisi"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
response = requests.get(url, headers=headers)

with open("sayfa.html", "w", encoding="utf-8") as f:
    f.write(response.text)

print("Status:", response.status_code)
print("İçerik uzunluğu:", len(response.text))