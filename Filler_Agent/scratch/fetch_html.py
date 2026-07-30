import requests

url = "https://docs.google.com/forms/d/e/1FAIpQLSfI88YkuUtB7ATZfWxpoCnV2fspIbh1fXYeIpI9UD2GP7TgaA/viewform"
try:
    res = requests.get(url, timeout=10)
    print("Status code:", res.status_code)
    print("Content length:", len(res.text))
    if "signin" in res.url.lower():
        print("Redirected to Sign In page:", res.url)
    else:
        print("Successful fetch, HTML snippet:")
        print(res.text[:1000])
except Exception as e:
    print("Error:", e)
