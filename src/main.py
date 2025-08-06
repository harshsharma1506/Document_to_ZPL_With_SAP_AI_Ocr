import os
from typing import cast
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# 🧾 Environment Variables
CLIENT_ID = os.getenv("DOX_CLIENT_ID")
CLIENT_SECRET = os.getenv("DOX_CLIENT_SECRET")
TOKEN_URL = cast(str, os.getenv("DOX_TOKEN_URL"))
API_URL = cast(str, os.getenv("DOX_API_URL"))
BASE_URL = cast(str, os.getenv("DOX_BASE_URL"))
SCHEMA_ID = cast(str, os.getenv("DOX_SCHEMA_ID"))
QR_DATA = cast(str, os.getenv("QR_DATA"))  # Custom QR content

def get_token():
  data = {
      'grant_type': 'client_credentials',
      'client_id': CLIENT_ID,
      'client_secret': CLIENT_SECRET
  }
  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  response = requests.post(TOKEN_URL, headers=headers, data=data)

  print("\n🔐 Raw token response status:", response.status_code)
  print("Raw response text:\n", response.text)

  response.raise_for_status()
  return response.json()['access_token']

def get_valid_clients():
  token = get_token()
  headers = {'Authorization': f'Bearer {token}'}
  endpoint = "/document-information-extraction/v1/clients"
  url = f"{BASE_URL}{endpoint}?limit=10"

  print(f"📡 Fetching client list from: {url}")
  response = requests.get(url, headers=headers)
  print(f"📥 Status: {response.status_code}")
  print("📄 Response JSON:")
  print(response.text)

  response.raise_for_status()
  data = response.json()

  print("\n📋 Available Clients:")
  for client in data.get("payload", []):
    print(f"- {client['clientId']}: {client['clientName']}")

  return data.get("payload", [])

def submit_po(file_path):
  token = get_token()
  headers = {'Authorization': f'Bearer {token}'}

  options = {
      "documentType": "purchaseOrder",
      "clientId": "default",
      "schemaId": SCHEMA_ID
  }

  files = {
      'file': ('po.txt', open(file_path, 'rb'), 'text/plain'),
      'options': (None, json.dumps(options), 'application/json')
  }

  print(f"📤 Uploading document: {file_path}")
  response = requests.post(API_URL, headers=headers, files=files)

  print(f"📥 Status code: {response.status_code}")
  print(response.text)
  response.raise_for_status()

  job_id = response.json()['id']
  print("✅ Job ID:", job_id)
  return job_id

def generate_zpl_from_result(result: dict) -> str:
  header = {
      field["name"]: field["value"]
      for field in result["extraction"]["headerFields"]
  }
  line_items = result["extraction"]["lineItems"]

  zpl = "^XA\n"
  zpl += "^CI28\n"  # UTF-8 encoding

  # Header
  zpl += "^CF0,30\n"
  zpl += f"^FO40,40^FD{header.get('senderName', 'N/A')}^FS\n"
  zpl += f"^FO40,75^FD{header.get('senderAddress', '')}, {header.get('senderCity', '')} {header.get('senderPostalCode', '')}, {header.get('senderCountryCode', '')}^FS\n"
  zpl += f"^FO40,110^FD{header.get('senderEmail', '')}^FS\n"

  # PO Info
  zpl += "^CF0,28\n"
  zpl += "^FO40,155^GB700,2,2^FS\n"
  zpl += f"^FO40,170^FDPO Number: {header.get('documentNumber', '')}^FS\n"
  zpl += f"^FO40,200^FDDate: {header.get('documentDate', '')}^FS\n"
  zpl += f"^FO40,230^FDTotal: ₹{header.get('netAmount', '')} {header.get('currencyCode', '')}^FS\n"

  # Items
  zpl += "^FO40,270^GB700,2,2^FS\n"
  zpl += "^FO40,285^FDItems:^FS\n"
  start_y = 320
  for i, group in enumerate(line_items[:3]):
    item = {field["name"]: field["value"] for field in group}
    desc = item.get("description", "N/A")
    qty = item.get("quantity", "N/A")
    price = item.get("unitPrice", "N/A")
    zpl += f"^FO60,{start_y}^FD• {desc} | Qty: {qty} | ₹{price}^FS\n"
    start_y += 35

  # Barcode
  zpl += "^FO40,450^BY2\n"
  zpl += "^BCN,80,Y,N,N\n"
  zpl += f"^FD{header.get('documentNumber', '')}^FS\n"

  # QR Code (non-intersecting)
  zpl += "^FO500,450\n"
  zpl += "^BQN,2,6\n"
  zpl += f"^FDLA,{QR_DATA}^FS\n"

  zpl += "^XZ"
  return zpl

def convert_zpl_to_pdf(zpl: str, printer_dpi: int = 8, width: float = 4, height: float = 6):
  url = f"http://api.labelary.com/v1/printers/{printer_dpi}dpmm/labels/{width}x{height}/"
  headers = {
      "Accept": "application/pdf",
      "Content-Type": "application/x-www-form-urlencoded"
  }
  response = requests.post(url, headers=headers, data=zpl.encode('utf-8'))
  response.raise_for_status()
  with open("label.pdf", "wb") as f:
    f.write(response.content)
  print("✅ PDF generated: label.pdf")

def poll_and_get_result(job_id):
  token = get_token()
  headers = {'Authorization': f'Bearer {token}'}

  import time
  status = "PENDING"
  job_url = f"{API_URL}/{job_id}"

  while status not in ["DONE", "FAILED"]:
    time.sleep(3)
    res = requests.get(job_url, headers=headers)
    res.raise_for_status()
    status = res.json()['status']
    print(f"⏳ Job Status: {status}")

  if status == "DONE":
    RESULT_PATH = f"/document-information-extraction/v1/document/jobs/{job_id}"
    result_url = f"{BASE_URL}{RESULT_PATH}"

    res = requests.get(result_url, headers=headers)
    print(f"📦 Result status code: {res.status_code}")
    print(f"📄 Raw result response:\n{res.text}")

    try:
      result = res.json()
      from pprint import pprint
      pprint(result)
      zpl = generate_zpl_from_result(result)
      print("\n📦 Generated Professional ZPL:\n")
      print(zpl)
      convert_zpl_to_pdf(zpl)
    except requests.exceptions.JSONDecodeError:
      print("⚠️ Failed to decode result JSON. Empty or invalid response.")

if __name__ == "__main__":
  clients = get_valid_clients()
  file_path = "Purchase.txt"
  job_id = submit_po(file_path)
  poll_and_get_result(job_id)
