import streamlit as st
from pdf2image import convert_from_path
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import numpy as np
import io
import zipfile

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="OCR Stress Test", layout="wide")

st.title("📄 OCR Stress Test Case Generator")
st.write("v1.2 - Fixed Error Handling & PDF Support")

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
        default=['skew']
    )
    intensity = st.slider("Intensity (ความแรง)", 0.1, 10.0, 2.0)
    out_fmt = st.selectbox("รูปแบบไฟล์ขาออก (Output Format)", ["PDF", "PNG", "JPG"])
    
    overlay_color = "#FFEB3B"
    if 'dimcolor' in selected_keys:
        overlay_color = st.color_picker("เลือกสีสำหรับโหมด Dim", "#FFEB3B")

# --- Effect Function ---
def apply_effect(img, mode, val, color_hex):
    temp_img = img.copy()
    if mode == 'skew': return temp_img.rotate(val, expand=True, fillcolor=(255, 255, 255))
    if mode == 'blur': return temp_img.filter(ImageFilter.GaussianBlur(radius=val))
    if mode == 'faded': 
        return ImageEnhance.Brightness(ImageEnhance.Contrast(temp_img).enhance(0.3)).enhance(1.1)
    if mode == 'noise':
        arr = np.array(temp_img)
        mask = np.random.randint(0, 255, (arr.shape[0], arr.shape[1], 1)) < (val * 5)
        arr[mask.all(axis=2)] = [60, 60, 60]
        return Image.fromarray(arr)
    if mode == 'lowres':
        w, h = temp_img.size
        s = temp_img.resize((max(1, int(w/val)), max(1, int(h/val))), resample=Image.NEAREST)
        return s.resize((w, h), resample=Image.NEAREST)
    if mode == 'watermark':
        draw = ImageDraw.Draw(temp_img)
        step = max(100, int(800 / val))
        for i in range(0, temp_img.height, step):
            draw.line((0, i, temp_img.width, i + step//2), fill=(220, 220, 220), width=int(val*5))
        return temp_img
    if mode == 'dimcolor':
        r, g, b = int(color_hex[1:3], 16), int(color_hex[3:5], 16), int(color_hex[5:7], 16)
        overlay = Image.new('RGB', temp_img.size, (r, g, b))
        return Image.blend(temp_img, overlay, min(val/10, 0.9))
    return temp_img

# --- Main Logic ---
uploaded_file = st.file_uploader("Upload PDF or Image", type=["pdf", "png", "jpg", "jpeg"])

if uploaded_file and selected_keys:
    if st.button("🚀 Generate & Prepare ZIP"):
        zip_buffer = io.BytesIO()
        try:
            with st.spinner('กำลังประมวลผล...'):
                file_ext = uploaded_file.name.split('.')[-1].lower()
                file_content = uploaded_file.read()
                
                # อ่านไฟล์แยกตามประเภท
                if file_ext == 'pdf':
                    # ลองอ่าน PDF
                    try:
                        pages = convert_from_path(file_content, 300)
                    except Exception as pdf_err:
                        st.error(f"PDF Error: ระบบไม่สามารถอ่าน PDF ได้ (อาจขาด Poppler) - {str(pdf_err)}")
                        st.stop()
                else:
                    pages = [Image.open(io.BytesIO(file_content)).convert("RGB")]
                
                base_name = uploaded_file.name.rsplit('.', 1)[0]
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for mode in selected_keys:
                        processed_images = []
                        for idx, page in enumerate(pages):
                            res_img = apply_effect(page, mode, intensity, overlay_color)
                            
                            if out_fmt != "PDF":
                                img_byte = io.BytesIO()
                                save_fmt = "JPEG" if out_fmt == "JPG" else out_fmt
                                res_img.save(img_byte, format=save_fmt)
                                suffix = f"_p{idx+1}" if len(pages) > 1 else ""
                                zip_file.writestr(f"{base_name}_{mode}{suffix}.{out_fmt.lower()}", img_byte.getvalue())
                            else:
                                processed_images.append(res_img)
                        
                        if out_fmt == "PDF" and processed_images:
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
        except Exception as main_e:
            st.error(f"เกิดข้อผิดพลาดรุนแรง: {str(main_e)}")
