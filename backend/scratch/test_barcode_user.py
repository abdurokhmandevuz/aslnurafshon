import urllib.request
import json

barcode = "4780032310174"
url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'AslNurafshon/1.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        if data.get('status') == 1:
            product = data.get('product', {})
            print("Found in Open Food Facts:")
            print(f"  Name: {product.get('product_name')}")
            print(f"  Brands: {product.get('brands')}")
        else:
            print("Not found in Open Food Facts")
except Exception as e:
    print(f"Error: {e}")
