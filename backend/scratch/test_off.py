import urllib.request
import json

def test_barcode(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AslNurafshon/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 1:
                product = data.get('product', {})
                print(f"[{barcode}] Found:")
                print(f"  Name: {product.get('product_name')}")
                print(f"  Name (uz): {product.get('product_name_uz')}")
                print(f"  Name (ru): {product.get('product_name_ru')}")
                print(f"  Brands: {product.get('brands')}")
                print(f"  Image: {product.get('image_url')}")
            else:
                print(f"[{barcode}] Not found in Open Food Facts")
    except Exception as e:
        print(f"[{barcode}] Error: {e}")

# Test with some common barcodes:
# Coca-Cola 1.5L barcode: 5449000131805
test_barcode("5449000131805")

# Test with Uzbekistan product barcode if any
# Snickers: 5000159461122
test_barcode("5000159461122")
