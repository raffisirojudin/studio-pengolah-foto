import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import io
import zipfile
import os

# Konfigurasi Halaman Web
st.set_page_config(page_title="Studio Pengolah Foto Massal", page_icon="🎨", layout="wide")

st.title("🎨 Studio Pengolah & Konverter Foto Massal")
st.write("Aplikasi serbaguna untuk edit foto massal, penyesuaian warna, watermark logo/teks, bulk rename, hingga konversi ke berbagai format & PDF.")

# ==================== SIDEBAR PENGATURAN ====================
st.sidebar.header("⚙️ 1. Format & Penamaan File")

# Moda Output: Gambar (ZIP) atau PDF
mode_output = st.sidebar.radio("Moda Hasil Akhir:", ["File Gambar Terpisah (ZIP)", "Gabung Jadi 1 File PDF"])

if mode_output == "File Gambar Terpisah (ZIP)":
    target_formats = st.sidebar.multiselect(
        "Format Output yang Diinginkan:",
        ["JPG", "PNG", "WEBP", "TIFF", "BMP", "GIF", "ICO"],
        default=["JPG"]
    )
else:
    target_formats = ["PDF"]

# Bulk Rename
st.sidebar.subheader("🏷️ Pola Nama File (Bulk Rename)")
prefix_nama = st.sidebar.text_input("Awalan Nama File:", "foto_produk")
pakai_penomoran = st.sidebar.checkbox("Tambahkan Penomoran Urut (_01, _02, dst)", value=True)

st.sidebar.markdown("---")
st.sidebar.header("📐 2. Dimensi & Potong (Crop)")

crop_ratio = st.sidebar.selectbox(
    "Potong Rasio Media Sosial:",
    ["Asli (Tanpa Crop)", "1:1 (Feed Instagram)", "9:16 (Story / TikTok)", "16:9 (Banner / Landscape)"]
)
max_width = st.sidebar.number_input("Lebar Maksimal Gambar (px):", min_value=16, max_value=3840, value=1920, step=100)
quality = st.sidebar.slider("Kualitas Kompresi (JPG/WEBP):", min_value=10, max_value=100, value=80)

st.sidebar.markdown("---")
st.sidebar.header("🎨 3. Filter & Efek Warna")
brightness = st.sidebar.slider("Kecerahan (Brightness):", 0.5, 1.5, 1.0, 0.05)
contrast = st.sidebar.slider("Kontras (Contrast):", 0.5, 1.5, 1.0, 0.05)
saturation = st.sidebar.slider("Saturasi Warna:", 0.0, 2.0, 1.0, 0.1)
is_grayscale = st.sidebar.checkbox("Ubah ke Hitam-Putih (Grayscale)")
apply_blur = st.sidebar.checkbox("Efek Blur Soft")

st.sidebar.markdown("---")
st.sidebar.header("💧 4. Watermark")
tipe_watermark = st.sidebar.radio("Jenis Watermark:", ["Tanpa Watermark", "Teks", "Logo Gambar (PNG)"])

teks_watermark = "CONFIDENTIAL"
ukuran_font = 36
logo_file = None
logo_scale = 20
opasitas = 120

if tipe_watermark == "Teks":
    teks_watermark = st.sidebar.text_input("Teks Watermark:", "CONFIDENTIAL")
    ukuran_font = st.sidebar.slider("Ukuran Font:", 12, 100, 36)
    opasitas = st.sidebar.slider("Transparansi Watermark:", 0, 255, 120)
elif tipe_watermark == "Logo Gambar (PNG)":
    logo_file = st.sidebar.file_uploader("Unggah Logo PNG (Background Transparan):", type=['png'])
    logo_scale = st.sidebar.slider("Ukuran Logo (% dari lebar foto):", 5, 50, 20)
    opasitas = st.sidebar.slider("Transparansi Logo:", 0, 255, 200)

st.sidebar.markdown("---")
st.sidebar.header("🔒 5. Privasi")
strip_exif = st.sidebar.checkbox("Hapus Metadata EXIF (GPS & Info Kamera)", value=True)


# ==================== FUNGSI PEMROSESAN ====================
def dapatkan_font(ukuran):
    font_paths = [
        "arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, ukuran)
        except Exception:
            continue
    return ImageFont.load_default()

def crop_gambar(img, ratio_str):
    if ratio_str.startswith("Asli"):
        return img
    ratios = {"1:1": (1, 1), "9:16": (9, 16), "16:9": (16, 9)}
    for k in ratios:
        if k in ratio_str:
            target_w, target_h = ratios[k]
            break
    else:
        return img

    w, h = img.size
    current_ratio = w / h
    target_ratio = target_w / target_h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        return img.crop((0, top, w, top + new_h))

def sesuaikan_warna(img):
    if is_grayscale:
        img = img.convert("L").convert("RGBA")
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if saturation != 1.0 and not is_grayscale:
        img = ImageEnhance.Color(img).enhance(saturation)
    if apply_blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    return img

def tempel_watermark(img):
    if tipe_watermark == "Tanpa Watermark":
        return img

    w, h = img.size
    watermark_layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))

    if tipe_watermark == "Teks":
        draw = ImageDraw.Draw(watermark_layer)
        font = dapatkan_font(ukuran_font)
        bbox = draw.textbbox((0, 0), teks_watermark, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pos_x = max(10, w - text_w - 20)
        pos_y = max(10, h - text_h - 20)
        draw.text((pos_x, pos_y), teks_watermark, font=font, fill=(255, 255, 255, opasitas))

    elif tipe_watermark == "Logo Gambar (PNG)" and logo_file is not None:
        logo = Image.open(logo_file).convert("RGBA")
        logo_w = int(w * (logo_scale / 100))
        logo_h = int(logo.height * (logo_w / logo.width))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

        if opasitas < 255:
            r, g, b, a = logo.split()
            a = a.point(lambda p: int(p * (opasitas / 255.0)))
            logo = Image.merge("RGBA", (r, g, b, a))

        pos_x = max(10, w - logo_w - 20)
        pos_y = max(10, h - logo_h - 20)
        watermark_layer.paste(logo, (pos_x, pos_y), logo)

    return Image.alpha_composite(img, watermark_layer)


# ==================== ANTARMUKA UTAMA ====================
uploaded_files = st.file_uploader(
    "Unggah foto-foto Anda di sini:", 
    type=['jpg', 'jpeg', 'png', 'webp', 'bmp', 'tiff'], 
    accept_multiple_files=True
)

if uploaded_files:
    if mode_output == "File Gambar Terpisah (ZIP)" and not target_formats:
        st.warning("⚠️ Pilih minimal satu format output di sidebar sebelah kiri!")
    else:
        st.info(f"Terdeteksi **{len(uploaded_files)} foto** siap diproses.")

        if st.button("🚀 Mulai Proses Semua Foto", type="primary"):
            progress_bar = st.progress(0)
            processed_images_for_pdf = []
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, uploaded_file in enumerate(uploaded_files):
                    # 1. Buka & Penyesuaian Dasar
                    img = Image.open(uploaded_file).convert("RGBA")
                    
                    # 2. Crop Aspect Ratio
                    img = crop_gambar(img, crop_ratio)

                    # 3. Resize Lebar Maksimal
                    orig_w, orig_h = img.size
                    ratio = min(max_width / orig_w, max_width / orig_h)
                    if ratio < 1.0:
                        new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
                        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    # 4. Filter Warna & Efek
                    img = sesuaikan_warna(img)

                    # 5. Watermark
                    img = tempel_watermark(img)

                    # 6. Menentukan Nama File Baru (Bulk Rename)
                    base_nama = prefix_nama if prefix_nama.strip() else "foto"
                    if pakai_penomoran:
                        nama_baru = f"{base_nama}_{idx+1:02d}"
                    else:
                        nama_baru = f"{base_nama}_{os.path.splitext(uploaded_file.name)[0]}"

                    # 7. Simpan Hasil Sesuai Format Pilihan
                    if mode_output == "Gabung Jadi 1 File PDF":
                        processed_images_for_pdf.append(img.convert("RGB"))
                    else:
                        for fmt in target_formats:
                            img_byte_arr = io.BytesIO()
                            
                            if fmt == "JPG":
                                img.convert("RGB").save(img_byte_arr, format='JPEG', quality=quality, optimize=True)
                                ext = "jpg"
                            elif fmt == "PNG":
                                img.save(img_byte_arr, format='PNG', optimize=True)
                                ext = "png"
                            elif fmt == "WEBP":
                                img.save(img_byte_arr, format='WEBP', quality=quality)
                                ext = "webp"
                            elif fmt == "TIFF":
                                img.convert("RGB").save(img_byte_arr, format='TIFF')
                                ext = "tiff"
                            elif fmt == "BMP":
                                img.convert("RGB").save(img_byte_arr, format='BMP')
                                ext = "bmp"
                            elif fmt == "GIF":
                                img.convert("P", palette=Image.ADAPTIVE).save(img_byte_arr, format='GIF')
                                ext = "gif"
                            elif fmt == "ICO":
                                ico_img = img.resize((256, 256), Image.Resampling.LANCZOS)
                                ico_img.save(img_byte_arr, format='ICO')
                                ext = "ico"

                            zip_file.writestr(f"{nama_baru}.{ext}", img_byte_arr.getvalue())

                    progress_bar.progress((idx + 1) / len(uploaded_files))

            st.success("✅ Seluruh foto berhasil diproses!")

            # Tombol Unduh
            if mode_output == "Gabung Jadi 1 File PDF":
                pdf_buffer = io.BytesIO()
                if processed_images_for_pdf:
                    processed_images_for_pdf[0].save(
                        pdf_buffer, format="PDF", save_all=True, append_images=processed_images_for_pdf[1:]
                    )
                    st.download_button(
                        label="📄 Unduh Dokumen PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"{prefix_nama}_dokumen.pdf",
                        mime="application/pdf"
                    )
            else:
                st.download_button(
                    label="📦 Unduh Semua Foto (File ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"{prefix_nama}_hasil.zip",
                    mime="application/zip"
                )
