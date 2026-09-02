import urllib.request
import ssl

url = "https://www.95598.cn/omg-static//omg-static/99304271451438878686301117855414.pdf"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    data = resp.read()
    print(f"Downloaded {len(data)} bytes! Status: {resp.status}")
    with open("crawler/data/documents/test_sample.pdf", "wb") as f:
        f.write(data)
    print("Saved to crawler/data/documents/test_sample.pdf")
