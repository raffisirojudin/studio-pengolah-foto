# ⚡ Super Photo Studio & Digital Tracker

Aplikasi web *all-in-one* berbasis **Python** dan **Streamlit** yang dirancang untuk pengolahan foto massal serta pelacakan jejak digital/metadata EXIF foto.

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PIL/Pillow](https://img.shields.io/badge/Pillow-000000?style=for-the-badge)

---

## ✨ Fitur Utama

Aplikasi ini terbagi menjadi 2 modul utama dalam bentuk Tab Navigasi:

### 🎨 1. Studio Pengolah Foto Massal
* **Konversi Format Lengkap:** Mengubah foto massal ke format JPG, PNG, WEBP, TIFF, BMP, GIF, ICO, atau menggabungkannya langsung menjadi **1 file PDF**.
* **Penamaan File Otomatis (Bulk Rename):** Pengaturan awalan nama dan nomor urut secara fleksibel.
* **Resizing & Fit-to-Box 1:1:** Mengubah ukuran foto responsive atau memasukkannya ke kanvas persegi 1:1 khusus untuk etalase *e-commerce*.
* **Kompresi Target Ukuran File:** Fitur khusus untuk membatasi ukuran file maksimal (misal: `< 200 KB`) untuk kebutuhan syarat pendaftaran CPNS/berkas administrasi.
* **Hapus Background AI:** Menghapus latar belakang foto secara otomatis berbasis AI menggunakan library `rembg`.
* **Watermarking Canggih:**
  * Watermark Teks Statik & Logo Gambar (PNG).
  * **Watermark Dinamis dari CSV/Excel:** Menempelkan teks watermark yang berbeda-beda untuk tiap foto berdasarkan nama file di spreadsheet.
* **Filter Warna:** Penyesuaian kecerahan, kontras, saturasi, dan mode hitam-putih (grayscale).

### 🔍 2. Pelacak Metadata EXIF & Peta GPS
* **Ekstraksi Metadata Perangkat:** Membaca merek HP/kamera, tipe perangkat, versi perangkat lunak, dan tanggal foto diambil.
* **Pelacak Lokasi Koordinat GPS:** Menampilkan titik koordinat *Latitude* dan *Longitude* pembuatan foto.
* **Peta Interaktif:** Mengintegrasikan titik lokasi ke dalam peta langsung di website serta menyediakan tautan cepat ke **Google Maps**.
* Trik: Kirim foto via WhatsApp sebagai Dokumen (Document) agar metadata EXIF tetap utuh dan dapat dilacak.

---

## 🛠️ Persyaratan File (Deployment)

Agar semua fitur AI dan manipulasi gambar berjalan lancar saat di-deploy ke **Streamlit Cloud**, pastikan proyek Anda memiliki file berikut:

### `requirements.txt`
```text
streamlit
pillow
pandas
openpyxl
rembg
onnxruntime
