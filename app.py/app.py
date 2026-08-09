import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from PIL.ExifTags import TAGS, GPSTAGS
import io
import zipfile
import os
import pandas as pd
import math  # <--- Tambahkan ini di bawah import pandas

# --- Fungsi Helper GPS & Google Maps ---
def dms_ke_deg(dms, ref):
    try:
        deg = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        dec = deg + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']:
            dec = -dec
        return dec
    except Exception:
        return None

def buat_link_gmaps(lat, lon):
    if lat is None or lon is None or math.isnan(lat) or math.isnan(lon):
        return ""
    return f"https://www.google.com/maps?q={lat},{lon}"
# Cek dukungan AI Background Removal (rembg)
try:
    from rembg import remove as remove_bg
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

# Konfigurasi Halaman Web
st.set_page_config(page_title="Super Photo Studio & Tracker", page_icon="⚡", layout="wide")

st.title("⚡ Super Photo Studio & Digital Tracker")

# Membuat 2 Tab utama
tab_studio, tab_tracker = st.tabs(["🎨 Pengolah Foto Massal", "🔍 Pelacak Metadata EXIF & Maps Converter"])

# ==============================================================================
# TAB 1: STUDIO PENGOLAH FOTO MASSAL
# ==============================================================================
with tab_studio:
    st.markdown("### 🎨 Studio Pengolah & Konverter Foto")
    
    # ------------------ SIDEBAR PENGATURAN ------------------
    st.sidebar.header("⚙️ 1. Format & Penamaan File")

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
    st.sidebar.header("📐 2. Dimensi & Fit-to-Box")

    mode_resize = st.sidebar.selectbox(
        "Mode Ukuran & Kanvas:",
        [
            "Asli (Tanpa Ubah Ukuran)",
            "Lebar Maksimal (Responsive)",
            "Fit-to-Box Square 1:1 (Kanvas Toko Online)",
            "Crop Aspect Ratio (1:1 / 9:16 / 16:9)"
        ]
    )

    max_width = 1920
    bg_canvas_color = "#FFFFFF"

    if mode_resize == "Lebar Maksimal (Responsive)":
        max_width = st.sidebar.number_input("Lebar Maksimal (px):", min_value=100, max_value=3840, value=1920, step=100)
    elif mode_resize == "Fit-to-Box Square 1:1 (Kanvas Toko Online)":
        max_width = st.sidebar.number_input("Ukuran Kanvas Persegi (px):", min_value=300, max_value=2400, value=1080, step=100)
        bg_canvas_color = st.sidebar.color_picker("Warna Latar Belakang Kanvas:", "#FFFFFF")
    elif mode_resize == "Crop Aspect Ratio (1:1 / 9:16 / 16:9)":
        crop_ratio = st.sidebar.selectbox("Pilih Rasio Crop:", ["1:1 (Square)", "9:16 (Story/TikTok)", "16:9 (Banner)"])
        max_width = st.sidebar.number_input("Lebar Maksimal (px):", min_value=300, max_value=3840, value=1920, step=100)

    st.sidebar.markdown("---")
    st.sidebar.header("🎯 3. Kompresi & Batas Ukuran File (CPNS/Admin)")
    enable_target_size = st.sidebar.checkbox("Aktifkan Batas Ukuran File Maksimal (Misal: < 200 KB)")
    target_size_kb = 200
    if enable_target_size:
        target_size_kb = st.sidebar.number_input("Ukuran File Maksimal (KB):", min_value=20, max_value=5000, value=200, step=10)
    quality = st.sidebar.slider("Kualitas Kompresi Dasar (JPG/WEBP):", 10, 100, 80)

    st.sidebar.markdown("---")
    st.sidebar.header("🤖 4. Hapus Background (AI Rembg)")
    do_remove_bg = False
    if REMBG_AVAILABLE:
        do_remove_bg = st.sidebar.checkbox("Hapus Background Otomatis dengan AI")
    else:
        st.sidebar.info("💡 Pustaka `rembg` belum terpasang di server untuk fitur Hapus BG AI.")

    st.sidebar.markdown("---")
    st.sidebar.header("🖼️ 5. Bingkai Promo (Frame Overlay)")
    frame_file = st.sidebar.file_uploader("Unggah Bingkai Promo (PNG Transparan):", type=['png'])

    st.sidebar.markdown("---")
    st.sidebar.header("💧 6. Watermark (Statik & Dinamis CSV)")
    tipe_watermark = st.sidebar.radio("Jenis Watermark:", ["Tanpa Watermark", "Teks Statik", "Logo Gambar (PNG)", "Dinamis dari File CSV/Excel"])

    teks_watermark = "CONFIDENTIAL"
    ukuran_font = 36
    logo_file = None
    logo_scale = 20
    opasitas = 120
    df_watermark = None

    if tipe_watermark == "Teks Statik":
        teks_watermark = st.sidebar.text_input("Teks Watermark:", "CONFIDENTIAL")
        ukuran_font = st.sidebar.slider("Ukuran Font:", 12, 100, 36)
        opasitas = st.sidebar.slider("Transparansi Watermark:", 0, 255, 120)
    elif tipe_watermark == "Logo Gambar (PNG)":
        logo_file = st.sidebar.file_uploader("Unggah Logo PNG:", type=['png'])
        logo_scale = st.sidebar.slider("Ukuran Logo (% dari foto):", 5, 50, 20)
        opasitas = st.sidebar.slider("Transparansi Logo:", 0, 255, 200)
    elif tipe_watermark == "Dinamis dari File CSV/Excel":
        csv_file = st.sidebar.file_uploader("Unggah File CSV/Excel (Kolom: 'filename' & 'text'):", type=['csv', 'xlsx'])
        if csv_file:
            try:
                if csv_file.name.endswith('.csv'):
                    df_watermark = pd.read_csv(csv_file)
                else:
                    df_watermark = pd.read_excel(csv_file)
                st.sidebar.success("✅ File CSV/Excel berhasil dibaca!")
            except Exception:
                st.sidebar.error("Gagal membaca file CSV/Excel.")
        ukuran_font = st.sidebar.slider("Ukuran Font Dinamis:", 12, 100, 36)
        opasitas = st.sidebar.slider("Transparansi Teks Dinamis:", 0, 255, 150)

    st.sidebar.markdown("---")
    st.sidebar.header("🎨 7. Filter Warna")
    brightness = st.sidebar.slider("Kecerahan:", 0.5, 1.5, 1.0, 0.05)
    contrast = st.sidebar.slider("Kontras:", 0.5, 1.5, 1.0, 0.05)
    saturation = st.sidebar.slider("Saturasi:", 0.0, 2.0, 1.0, 0.1)
    is_grayscale = st.sidebar.checkbox("Ubah ke Hitam-Putih")

    # Helper Functions
    def dapatkan_font(ukuran):
        font_paths = ["arial.ttf", "C:\\Windows\\Fonts\\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, ukuran)
            except Exception:
                continue
        return ImageFont.load_default()

    def hex_to_rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    def apply_fit_to_box(img, target_size, bg_hex):
        img_w, img_h = img.size
        ratio = min(target_size / img_w, target_size / img_h)
        new_w, new_h = int(img_w * ratio), int(img_h * ratio)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bg_color = hex_to_rgb(bg_hex) + (255,)
        canvas = Image.new("RGBA", (target_size, target_size), bg_color)
        canvas.paste(resized, ((target_size - new_w) // 2, (target_size - new_h) // 2), resized)
        return canvas

    def crop_gambar_ratio(img, ratio_str):
        ratios = {"1:1": (1, 1), "9:16": (9, 16), "16:9": (16, 9)}
        target_w, target_h = (1, 1)
        for k in ratios:
            if k in ratio_str:
                target_w, target_h = ratios[k]
                break
        w, h = img.size
        current_ratio, target_ratio = w / h, target_w / target_h

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
        return img

    def tempel_watermark(img, nama_file_asli):
        if tipe_watermark == "Tanpa Watermark":
            return img

        w, h = img.size
        watermark_layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)

        teks_dipakai = ""
        if tipe_watermark == "Teks Statik":
            teks_dipakai = teks_watermark
        elif tipe_watermark == "Dinamis dari File CSV/Excel" and df_watermark is not None:
            row = df_watermark[df_watermark['filename'].astype(str).str.contains(nama_file_asli, case=False, na=False)]
            if not row.empty:
                teks_dipakai = str(row.iloc[0]['text'])

        if teks_dipakai:
            font = dapatkan_font(ukuran_font)
            bbox = draw.textbbox((0, 0), teks_dipakai, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text((max(10, w - text_w - 20), max(10, h - text_h - 20)), teks_dipakai, font=font, fill=(255, 255, 255, opasitas))

        elif tipe_watermark == "Logo Gambar (PNG)" and logo_file is not None:
            logo = Image.open(logo_file).convert("RGBA")
            logo_w = int(w * (logo_scale / 100))
            logo_h = int(logo.height * (logo_w / logo.width))
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

            if opasitas < 255:
                r, g, b, a = logo.split()
                a = a.point(lambda p: int(p * (opasitas / 255.0)))
                logo = Image.merge("RGBA", (r, g, b, a))

            watermark_layer.paste(logo, (max(10, w - logo_w - 20), max(10, h - logo_h - 20)), logo)

        return Image.alpha_composite(img, watermark_layer)

    def kompres_ke_target_kb(img_rgb, fmt, max_kb, base_q):
        target_bytes = max_kb * 1024
        curr_q = base_q
        while curr_q >= 10:
            buf = io.BytesIO()
            if fmt == "JPG":
                img_rgb.save(buf, format='JPEG', quality=curr_q, optimize=True)
            elif fmt == "WEBP":
                img_rgb.save(buf, format='WEBP', quality=curr_q)
            else:
                img_rgb.save(buf, format=fmt)
                return buf.getvalue()

            if buf.tell() <= target_bytes or curr_q <= 15:
                return buf.getvalue()
            curr_q -= 5
        return buf.getvalue()

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
                        img = Image.open(uploaded_file).convert("RGBA")
                        
                        if do_remove_bg and REMBG_AVAILABLE:
                            img = remove_bg(img)

                        if mode_resize == "Fit-to-Box Square 1:1 (Kanvas Toko Online)":
                            img = apply_fit_to_box(img, max_width, bg_canvas_color)
                        elif mode_resize == "Crop Aspect Ratio (1:1 / 9:16 / 16:9)":
                            img = crop_gambar_ratio(img, crop_ratio)
                            orig_w, orig_h = img.size
                            ratio = min(max_width / orig_w, max_width / orig_h)
                            if ratio < 1.0:
                                img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.LANCZOS)
                        elif mode_resize == "Lebar Maksimal (Responsive)":
                            orig_w, orig_h = img.size
                            ratio = min(max_width / orig_w, max_width / orig_h)
                            if ratio < 1.0:
                                img = img.resize((int(orig_w * ratio), int(orig_h * ratio)), Image.Resampling.LANCZOS)

                        img = sesuaikan_warna(img)

                        if frame_file is not None:
                            frame_img = Image.open(frame_file).convert("RGBA")
                            frame_resized = frame_img.resize(img.size, Image.Resampling.LANCZOS)
                            img = Image.alpha_composite(img, frame_resized)

                        img = tempel_watermark(img, uploaded_file.name)

                        base_nama = prefix_nama if prefix_nama.strip() else "foto"
                        nama_baru = f"{base_nama}_{idx+1:02d}" if pakai_penomoran else f"{base_nama}_{os.path.splitext(uploaded_file.name)[0]}"

                        if mode_output == "Gabung Jadi 1 File PDF":
                            processed_images_for_pdf.append(img.convert("RGB"))
                        else:
                            for fmt in target_formats:
                                img_rgb = img.convert("RGB") if fmt in ["JPG", "TIFF", "BMP"] else img
                                
                                if enable_target_size and fmt in ["JPG", "WEBP"]:
                                    file_data = kompres_ke_target_kb(img_rgb, fmt, target_size_kb, quality)
                                else:
                                    buf = io.BytesIO()
                                    if fmt == "JPG":
                                        img_rgb.save(buf, format='JPEG', quality=quality, optimize=True)
                                    elif fmt == "PNG":
                                        img.save(buf, format='PNG', optimize=True)
                                    elif fmt == "WEBP":
                                        img.save(buf, format='WEBP', quality=quality)
                                    elif fmt == "TIFF":
                                        img_rgb.save(buf, format='TIFF')
                                    elif fmt == "BMP":
                                        img_rgb.save(buf, format='BMP')
                                    elif fmt == "GIF":
                                        img.convert("P", palette=Image.ADAPTIVE).save(buf, format='GIF')
                                    elif fmt == "ICO":
                                        img.resize((256, 256), Image.Resampling.LANCZOS).save(buf, format='ICO')
                                    file_data = buf.getvalue()

                                ext = fmt.lower()
                                zip_file.writestr(f"{nama_baru}.{ext}", file_data)

                        progress_bar.progress((idx + 1) / len(uploaded_files))

                st.success("✅ Seluruh foto berhasil diproses!")

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


# ==============================================================================
# TAB 2: PELACAK METADATA EXIF & KONVERTER GOOGLE MAPS
# ==============================================================================
with tab_tracker:
    st.markdown("### 🔍 Pelacak EXIF Foto & Generator Link Google Maps")

    def buat_link_gmaps(latitude, longitude):
        return f"https://www.google.com/maps?q={latitude},{longitude}"

    def dms_ke_deg(dms, ref):
        deg = float(dms[0]) + float(dms[1]) / 60.0 + float(dms[2]) / 3600.0
        return -deg if ref in ['S', 'W'] else deg

    sub_tab1, sub_tab2 = st.tabs(["📸 Extract Auto dari Foto", "🌐 Input Koordinat Manual"])

    # ------------------ SUB TAB 1: ESTRAKSI DARI FOTO ------------------
    with sub_tab1:
    st.write("Unggah foto asli untuk mengekstrak informasi kamera dan mengubah lokasi GPS foto menjadi Link Google Maps.")
    file_lacak = st.file_uploader("Unggah foto tunggal:", type=['jpg', 'jpeg', 'tiff'], key="uploader_lacak")

    if file_lacak:
        try:
            img_lacak = Image.open(file_lacak)
            exif_data = img_lacak._getexif()

            col1, col2 = st.columns([1, 1])
            with col1:
                st.image(img_lacak, caption="Foto yang Diunggah", use_container_width=True)

            with col2:
                if not exif_data:
                    st.warning("⚠️ Foto ini TIDAK memiliki metadata EXIF (kemungkinan dikirim via WhatsApp biasa atau metadatanya sudah dihapus).")
                else:
                    st.success("✅ Metadata EXIF terdeteksi!")

                    gps_info = {}
                    info_perangkat = {}

                    for tag_id, val in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name == "GPSInfo":
                            for g_tag in val:
                                g_name = GPSTAGS.get(g_tag, g_tag)
                                gps_info[g_name] = val[g_tag]
                        elif tag_name in ['Make', 'Model', 'DateTimeOriginal', 'Software', 'Orientation']:
                            val_str = str(val).strip()
                            info_perangkat[tag_name] = val_str if val_str else "Tidak ada"

                    st.subheader("📱 Informasi Perangkat & Waktu")
                    st.write(f"**Make:** `{info_perangkat.get('Make', 'Tidak ada')}`")
                    st.write(f"**Model:** `{info_perangkat.get('Model', 'Tidak ada')}`")
                    st.write(f"**DateTimeOriginal:** `{info_perangkat.get('DateTimeOriginal', 'Tidak ada')}`")
                    st.write(f"**Software:** `{info_perangkat.get('Software', 'Tidak ada')}`")

                    # Ekstraksi GPS aman
                    lat, lon = None, None
                    if gps_info and 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                        lat = dms_ke_deg(gps_info['GPSLatitude'], gps_info.get('GPSLatitudeRef', 'N'))
                        lon = dms_ke_deg(gps_info['GPSLongitude'], gps_info.get('GPSLongitudeRef', 'E'))

                    if lat is not None and lon is not None and not math.isnan(lat) and not math.isnan(lon):
                        link_gmaps = buat_link_gmaps(lat, lon)

                        st.subheader("📍 Lokasi GPS & Link Google Maps")
                        st.write(f"**Latitude:** `{lat:.6f}`")
                        st.write(f"**Longitude:** `{lon:.6f}`")
                        
                        st.text_input("Tautan Langsung Google Maps:", value=link_gmaps, key="link_exif_out")
                        st.markdown(f"👉 [Klik di sini untuk buka lokasi di Google Maps]({link_gmaps})")

                        # Peta Interaktif Streamlit
                        df_map = pd.DataFrame({'lat': [lat], 'lon': [lon]})
                        st.map(df_map)
                    else:
                        st.info("ℹ️ Informasi perangkat ditemukan, namun koordinat lokasi GPS tidak terlampir atau tidak valid pada foto ini.")
        except Exception as e:
            st.error(f"Gagal membaca metadata foto: {e}")

    # ------------------ SUB TAB 2: KONVERTER MANUALL ------------------
    with sub_tab2:
        st.write("Masukkan koordinat manual di bawah ini untuk menghasilkan link Google Maps dan melihat titik lokasinya di peta.")

        jenis_input = st.radio("Pilih Format Koordinat Input:", ["Desimal (contoh: -6.2088, 106.8456)", "DMS / Derajat Menit Detik (contoh: 6°12'31.68\" S)"])

        if jenis_input == "Desimal (contoh: -6.2088, 106.8456)":
            col_lat, col_lon = st.columns(2)
            with col_lat:
                val_lat = st.number_input("Latitude (Lintang):", value=-6.208800, format="%.6f")
            with col_lon:
                val_lon = st.number_input("Longitude (Bujur):", value=106.845600, format="%.6f")

            link_manual = buat_link_gmaps(val_lat, val_lon)

            st.success("✅ Link Google Maps Berhasil Dibuat!")
            st.text_input("URL Google Maps:", value=link_manual, key="manual_dec_link")
            st.markdown(f"👉 [Buka Titik Lokasi di Google Maps]({link_manual})")

            df_map_manual = pd.DataFrame({'lat': [val_lat], 'lon': [val_lon]})
            st.map(df_map_manual)

        else:
            st.subheader("Konversi DMS ke Google Maps")
            c1, c2 = st.columns(2)

            with c1:
                st.write("**Latitude (Lintang)**")
                lat_d = st.number_input("Derajat (°)", min_value=0, max_value=90, value=6, key="dms_lat_d")
                lat_m = st.number_input("Menit (')", min_value=0, max_value=59, value=12, key="dms_lat_m")
                lat_s = st.number_input("Detik (\")", min_value=0.0, max_value=59.99, value=31.68, key="dms_lat_s")
                lat_ref = st.selectbox("Arah Arah Lintang:", ["S (Selatan / South)", "N (Utara / North)"])

            with c2:
                st.write("**Longitude (Bujur)**")
                lon_d = st.number_input("Derajat (°)", min_value=0, max_value=180, value=106, key="dms_lon_d")
                lon_m = st.number_input("Menit (')", min_value=0, max_value=59, value=50, key="dms_lon_m")
                lon_s = st.number_input("Detik (\")", min_value=0.0, max_value=59.99, value=44.16, key="dms_lon_s")
                lon_ref = st.selectbox("Arah Bujur:", ["E (Timur / East)", "W (Barat / West)"])

            lat_dec = (lat_d + lat_m/60.0 + lat_s/3600.0) * (-1 if lat_ref.startswith('S') else 1)
            lon_dec = (lon_d + lon_m/60.0 + lon_s/3600.0) * (-1 if lon_ref.startswith('W') else 1)

            link_dms = buat_link_gmaps(lat_dec, lon_dec)

            st.success("✅ Koordinat DMS Berhasil Dikonversi ke Google Maps!")
            st.write(f"**Hasil Desimal:** Latitude `{lat_dec:.6f}`, Longitude `{lon_dec:.6f}`")
            st.text_input("URL Google Maps:", value=link_dms, key="manual_dms_link")
            st.markdown(f"👉 [Buka Titik Lokasi di Google Maps]({link_dms})")

            df_map_dms = pd.DataFrame({'lat': [lat_dec], 'lon': [lon_dec]})
            st.map(df_map_dms)
