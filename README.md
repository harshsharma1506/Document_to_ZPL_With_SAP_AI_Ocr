# 🧾 SAP Document AI Label Generator

This project integrates with **SAP Document Information Extraction (DOX)** service to extract key fields from purchase order documents and generate a **professional shipping label** in **ZPL (Zebra Programming Language)** format. The label is then converted to **PDF using Labelary API** for preview and printing.

## 🚀 Features

- 📄 Uploads and processes PO documents (`.txt`/`.pdf`) via SAP DOX
- 🧠 Uses schema-based AI model to extract:
  - Sender Name, Address, Email
  - PO Number, Date, Net Amount, Currency
  - Line Item Description, Quantity, Unit Price
- 🎯 Dynamically generates a clean ZPL shipping label
- 🔄 Converts ZPL to PDF using Labelary
- ✅ Secure token-based authentication using `.env`
- 📦 Generates result label with QR code and barcode

## 📸 Screenshots

> *(Add these after you run the app)*
- `label.pdf` preview
- Terminal output during job polling and label generation
- SAP Document AI response (sample)

## 🧩 Architecture Overview

```plaintext
SAP DOX API  →  Extracted JSON  →  ZPL Generator  →  Labelary PDF Preview
         ↑          ↓
     OAuth Token  .env config
