import streamlit as st
import pypdfium2 as pdfium
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np
import io
import zipfile

st.set_page_config(page_title="OCR Stress Test", layout="wide")
st.title("📄 OCR Stress Test Case Generator")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    mode_options = {'skew': 'Skew', 'blur': 'Blur', 'faded': 'Faded', 'noise': 'Noise', 'lowres': 'LowRes', 'watermark': 'Watermark', 'dimcolor': 'Dim'}
    selected_keys = st.multiselect("เลือกโหมด:", list(mode_options.keys()), format_func=lambda x: mode_options[x], default=['skew'])
    intensity = st.slider("Intensity", 0.1, 10.0, 2.0)
    out_fmt = st.selectbox("Output Format", ["PDF", "PNG", "JPG"])
    overlay_color = st.color_picker("เลือกสี Dim", "#FFEB3B") if 'dimcolor' in selected_keys else "#FFEB3B"

# --- Effect Functions (เหมือนเดิมที่คุณมี) ---
def apply_effect(img, mode, val, color_hex):
    temp = img.copy()
    if mode == 'skew': return temp.rotate(val, expand=True, fillcolor=(255, 255, 255))
    if mode == 'blur': return temp.filter(ImageFilter.GaussianBlur(radius=val))
    if mode == 'faded': return ImageEnhance.Brightness(ImageEnhance.Contrast(temp).enhance(0.3)).enhance(1.1)
    if mode == 'noise':
        arr = np.array(temp)
        mask = np.random.randint(0, 255, (arr.shape[0], arr.shape[1], 1)) < (val * 5)
        arr[mask.all(axis=2)] = [60, 60, 60]
        return Image.fromarray(arr)
    if mode == 'lowres':
        w, h = temp.size
        s = temp.resize((max(1, int(w/val)), max(1, int(h/val))), resample=Image.NEAREST)
        return s.resize((w, h), resample=Image.NEAREST)
    if mode == 'watermark':
        draw = ImageDraw.Draw(temp)
        step = max(100, int(800 / val))
        for i in range(0, temp.height, step): draw.line((0, i, temp.width, i + step//2), fill=(220, 220, 220), width=int(val*5))
        return temp
    if mode == 'dimcolor':
        r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
        return Image.blend(temp, Image.new('RGB', temp.size, (r, g, b)), min(val/10, 0.9))
    return temp

# --- Logic (เปลี่ยนการอ่าน PDF) ---
uploaded_file = st.file_uploader("Upload PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and selected_keys:
    if st.button("🚀 Generate & Prepare ZIP"):
        zip_buffer = io.BytesIO()
        try:
            with st.spinner('Processing...'):
                raw_data = uploaded_file.read()
                if uploaded_file.name.lower().endswith('.pdf'):
                    # ใช้ pypdfium2 แทน pdf2image (ไม่ต้องใช้ Poppler)
                    pdf = pdfium.PdfDocument(raw_data)
                    pages = [pdf[i].render(scale=2).to_pil() for i in range(len(pdf))]
                else:
                    pages = [Image.open(io.BytesIO(raw_data)).convert("RGB")]
                
                base_name = uploaded_file.name.rsplit('.', 1)[0]
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for mode in selected_keys:
                        processed_imgs = [apply_effect(p, mode, intensity, overlay_color) for p in pages]
                        if out_fmt == "PDF":
                            buf = io.BytesIO()
                            processed_imgs[0].save(buf, format="PDF", save_all=True, append_images=processed_imgs[1:])
                            zip_file.writestr(f"{base_name}_{mode}.pdf", buf.getvalue())
                        else:
                            for idx, img in enumerate(processed_imgs):
                                buf = io.BytesIO()
                                img.save(buf, format="JPEG" if out_fmt=="JPG" else "PNG")
                                suffix = f"_p{idx+1}" if len(processed_imgs) > 1 else ""
                                zip_file.writestr(f"{base_name}_{mode}{suffix}.{out_fmt.lower()}", buf.getvalue())
                
                st.success("สำเร็จแล้ว!")
                st.download_button("📥 Download ZIP", zip_buffer.getvalue(), f"{base_name}_test_cases.zip")
        except Exception as final_e:
            st.error(f"Error: {str(final_e)}")
