import streamlit as st
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np
import io
import zipfile

st.set_page_config(page_title="OCR Stress Test", layout="wide")

st.title("📄 OCR Stress Test Case Generator")
st.write("อัปโหลดไฟล์เดียว เพื่อสร้างชุดทดสอบแยกตามโหมดโดยอัตโนมัติ (PDF/Images)")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Settings")
    mode_options = {
        'skew': 'Skew (เอียง)',
        'blur': 'Blur (เบลอ)',
        'faded': 'Faded (จาง)',
        'noise': 'Noise (จุดรบกวน)',
        'lowres': 'Low Res (ภาพแตก)',
        'watermark': 'Watermark (แถบคาด)',
        'dimcolor': 'Dim (สีทับ)'
    }
    selected_keys = st.multiselect(
        "เลือกโหมดที่ต้องการสร้างไฟล์:",
        list(mode_options.keys()),
        format_func=lambda x: mode_options[x],
        default=['skew', 'blur']
    )
    intensity = st.slider("Intensity (ความแรง)", 0.1, 10.0, 2.0)
    out_fmt = st.selectbox("รูปแบบไฟล์ขาออก (Output Format)", ["PDF", "PNG", "JPG"])
    overlay_color = "#FFEB3B"
    if 'dimcolor' in selected_keys:
        overlay_color = st.color_picker("เลือกสีสำหรับโหมด Dim", "#FFEB3B")

# --- Helper Function ---
def apply_effect(img, mode, val, color_hex):
    img = img.copy()
    if mode == 'skew': return img.rotate(val, expand=True, fillcolor=(255, 255, 255))
    if mode == 'blur': return img.filter(ImageFilter.GaussianBlur(radius=val))
    if mode == 'faded': 
        return ImageEnhance.Brightness(ImageEnhance.Contrast(img).enhance(0.3)).enhance(1.1)
    if mode == 'noise':
        arr = np.array(img)
        mask = np.random.randint(0, 255, (arr.shape[0], arr.shape[1], 1)) < (val * 5)
        arr[mask.all(axis=2)] = [60, 60, 60]
        return Image.fromarray(arr)
    if mode == 'lowres':
        w, h = img.size
        s = img.resize((max(1, int(w/val)), max(1, int(h/val))), resample=Image.NEAREST)
        return s.resize((w, h), resample=Image.NEAREST)
    if mode == 'watermark':
        draw = ImageDraw.Draw(img)
        step = max(100, int(800 / val))
        for i in range(0, img.height, step):
            draw.line((0, i, img.width, i + step//2), fill=(220, 220, 220), width=int(val*5))
        return img
    if mode == 'dimcolor':
        r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
        overlay = Image.new('RGB', img.size, (r, g, b))
        return Image.blend(img, overlay, min(val/10, 0.9))
    return img

# --- UI Logic ---
uploaded_file = st.file_uploader("Upload PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and selected_keys:
    if st.button("🚀 Generate & Prepare ZIP"):
        zip_buffer = io.BytesIO()
        try:
            with st.spinner('กำลังประมวลผลไฟล์...'):
                input_data = uploaded_file.read()
                if uploaded_file.name.lower().endswith('.pdf'):
                    # แก้ไขส่วนการอ่านไฟล์ PDF ให้รองรับ Bytes โดยตรง
                    original_pages = convert_from_path(input_data, 300)
                else:
                    original_pages = [Image.open(io.BytesIO(input_data)).convert("RGB")]
                
                base_name = uploaded_file.name.rsplit('.', 1)[0]
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for mode in selected_keys:
                        processed_images = []
                        for idx, page in enumerate(original_pages):
                            res_img = apply_effect(page, mode, intensity, overlay_color)
                            
                            if out_fmt != "PDF":
                                img_byte = io.BytesIO()
                                res_img.save(img_byte, format=out_fmt)
                                page_suffix = f"_page{idx+1}" if len(original_pages) > 1 else ""
                                zip_file.writestr(f"{base_name}_{mode}{page_suffix}.{out_fmt.lower()}", img_byte.getvalue())
                            else:
                                processed_images.append(res_img)
                        
                        if out_fmt == "PDF":
                            pdf_byte = io.BytesIO()
                            processed_images[0].save(pdf_byte, format="PDF", save_all=True, append_images=processed_images[1:])
                            zip_file.writestr(f"{base_name}_{mode}.pdf", pdf_byte.getvalue())
                
                st.success(f"สร้างไฟล์เสร็จเรียบร้อย! (รวม {len(selected_keys)} โหมด)")
                st.download_button(
                    label="📥 Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"{base_name}_test_cases.zip",
                    mime="application/zip"
                )
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}") # แก้ไขตัวแปร error ให้ถูกต้อง
