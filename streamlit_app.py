import streamlit as st
import fitz  # PyMuPDF
import chardet
import io
import zipfile
from docx import Document
from docx.shared import Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import tempfile
import os
from PIL import Image, ImageFont, ImageDraw
import pytesseract
import numpy as np
import cv2

# Set page configuration
st.set_page_config(
    page_title="PDF Text Extractor with Indic Support",
    page_icon="📄",
    layout="wide"
)

# Enhanced OCR configuration for Indic languages
INDIC_LANGUAGES = {
    'hindi': 'hin',
    'sanskrit': 'san',
    'bengali': 'ben',
    'gujarati': 'guj',
    'kannada': 'kan',
    'malayalam': 'mal',
    'marathi': 'mar',
    'punjabi': 'pan',
    'tamil': 'tam',
    'telugu': 'tel',
    'urdu': 'urd',
    'english': 'eng'
}

# Indic font families that work well with OCR
INDIC_FONTS = {
    'devanagari': ['Mangal', 'Nirmala UI', 'Sanskrit 2003', 'Kokila', 'Aparajita'],
    'bengali': ['Nirmala UI', 'Shonar Bangla', 'Vrinda'],
    'gujarati': ['Nirmala UI', 'Shruti'],
    'kannada': ['Nirmala UI', 'Tunga'],
    'malayalam': ['Nirmala UI', 'Kartika'],
    'tamil': ['Nirmala UI', 'Latha'],
    'telugu': ['Nirmala UI', 'Gautami'],
    'punjabi': ['Nirmala UI', 'Raavi']
}


def preprocess_image_for_indic_ocr(image, language_script='devanagari'):
    """Enhanced image preprocessing specifically for Indic scripts"""
    try:
        # Convert PIL to OpenCV format
        img_array = np.array(image)

        # Convert to grayscale if not already
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Apply different preprocessing based on script
        if language_script in ['devanagari', 'bengali', 'gujarati']:
            # For Devanagari-based scripts
            # Apply slight blur to connect broken characters
            blurred = cv2.GaussianBlur(gray, (1, 1), 0)

            # Adaptive thresholding works better for Indic scripts
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 11, 2)
        else:
            # For other scripts
            # Standard binary thresholding
            _, thresh = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological operations to clean up the image
        kernel = np.ones((1, 1), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Convert back to PIL Image
        return Image.fromarray(cleaned)

    except Exception as e:
        st.warning(
            f"Image preprocessing failed: {str(e)}, using original image")
        return image


def extract_text_with_indic_ocr(image, selected_languages, preprocessing=True):
    """Extract text using Tesseract with Indic language support"""
    try:
        # Preprocess image if enabled
        if preprocessing:
            # Determine script type from languages
            script_type = 'devanagari'  # default
            if any(lang in ['bengali', 'bengali'] for lang in selected_languages):
                script_type = 'bengali'
            elif any(lang in ['tamil', 'malayalam', 'kannada', 'telugu'] for lang in selected_languages):
                script_type = 'south_indian'

            processed_image = preprocess_image_for_indic_ocr(
                image, script_type)
        else:
            processed_image = image

        # Create language string for Tesseract
        lang_codes = [INDIC_LANGUAGES.get(lang, 'eng')
                      for lang in selected_languages]
        lang_string = '+'.join(lang_codes)

        # Enhanced OCR configuration for Indic languages
        custom_config = r'''--oem 3 --psm 6 
        -c tessedit_char_whitelist=
        -c preserve_interword_spaces=1
        -c load_system_dawg=false
        -c load_freq_dawg=false
        -c load_punc_dawg=false
        -c load_number_dawg=false
        -c load_unambig_dawg=false
        -c load_bigram_dawg=false
        -c load_fixed_length_dawgs=false'''

        # Try different PSM modes for better Indic text recognition
        psm_modes = [6, 4, 3, 8, 13]  # Different page segmentation modes
        best_text = ""
        best_confidence = 0

        for psm in psm_modes:
            try:
                config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'

                # Get OCR result with confidence scores
                data = pytesseract.image_to_data(processed_image, lang=lang_string,
                                                 config=config, output_type=pytesseract.Output.DICT)

                # Calculate average confidence
                confidences = [int(conf)
                               for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / \
                    len(confidences) if confidences else 0

                # Get text
                text = pytesseract.image_to_string(
                    processed_image, lang=lang_string, config=config)

                # Keep the result with highest confidence
                if avg_confidence > best_confidence and text.strip():
                    best_confidence = avg_confidence
                    best_text = text

            except Exception as e:
                continue

        return best_text, best_confidence

    except Exception as e:
        st.error(f"OCR extraction failed: {str(e)}")
        return "", 0


def set_indic_font_in_docx(doc, font_name='Nirmala UI'):
    """Set Indic-compatible font for Word document"""
    try:
        # Set default font for the document
        styles = doc.styles
        style = styles['Normal']
        font = style.font
        font.name = font_name

        # Also set for complex scripts (required for Indic text)
        rFonts = style.element.rPr.rFonts if style.element.rPr is not None else None
        if rFonts is not None:
            rFonts.set(qn('w:cs'), font_name)  # Complex Script font
            rFonts.set(qn('w:ascii'), font_name)  # ASCII font
            rFonts.set(qn('w:hAnsi'), font_name)  # High ANSI font

    except Exception as e:
        st.warning(f"Could not set Indic font: {str(e)}")


def extract_text_from_pdf(pdf_file, use_ocr=False, selected_languages=['hindi', 'english'],
                          enable_preprocessing=True, selected_font='Nirmala UI'):
    """Extract text from PDF file using PyMuPDF with enhanced Indic OCR support"""
    try:
        # Check file size first
        file_size_mb = pdf_file.size / (1024 * 1024)

        # Check if file is too small to be a valid PDF
        if pdf_file.size < 100:
            st.error(
                f"File is too small ({pdf_file.size} bytes) to be a valid PDF. Please check your upload.")
            return None

        if file_size_mb > 50:
            st.warning(
                f"Large file detected ({file_size_mb:.1f}MB). Processing may take a while.")

        # Read PDF from uploaded file
        pdf_bytes = pdf_file.read()

        # Check if it's a valid PDF by looking at the header
        if not pdf_bytes.startswith(b'%PDF'):
            st.error(
                "This doesn't appear to be a valid PDF file. Please check the file format.")
            return None

        # Try to open the PDF
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as pdf_error:
            st.error(f"Cannot open PDF file: {str(pdf_error)}")
            st.info("This might be a corrupted PDF or a PDF with restrictions.")
            return None

        # Check page count
        try:
            page_count = len(pdf_document)
        except:
            try:
                page_count = pdf_document.page_count
            except:
                page_count = pdf_document.pageCount

        if page_count == 0:
            st.error("PDF has no pages or pages cannot be accessed.")
            pdf_document.close()
            return None

        st.info(f"PDF loaded successfully: {page_count} pages found")
        st.info(f"OCR Languages: {', '.join(selected_languages)}")
        if use_ocr:
            st.info(f"Target Font: {selected_font}")

        if page_count > 500:
            st.warning(
                f"Large document ({page_count} pages). Processing may take time.")

        text_content = ""
        pages_with_text = 0
        pages_without_text = 0
        ocr_pages = 0

        # Add progress bar for large documents
        progress_bar = None
        if page_count > 5 or use_ocr:
            progress_bar = st.progress(0)

        for page_num in range(page_count):
            try:
                # Access page
                try:
                    page = pdf_document[page_num]
                except:
                    try:
                        page = pdf_document.load_page(page_num)
                    except:
                        page = pdf_document.loadPage(page_num)

                # First try regular text extraction
                page_text = page.get_text()

                # If no text found and OCR is enabled, try enhanced Indic OCR
                if (not page_text.strip() or len(page_text.strip()) < 10) and use_ocr:
                    try:
                        # Convert page to high-resolution image for better OCR
                        # Higher resolution for Indic text
                        mat = fitz.Matrix(3.0, 3.0)
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")

                        # Convert to PIL Image
                        img = Image.open(io.BytesIO(img_data))

                        # Use enhanced Indic OCR
                        ocr_text, confidence = extract_text_with_indic_ocr(
                            img, selected_languages, enable_preprocessing)

                        if ocr_text.strip():
                            page_text = f"[OCR EXTRACTED - Confidence: {confidence:.1f}%]\n{ocr_text}"
                            st.success(
                                f"OCR extracted text from page {page_num + 1} (Confidence: {confidence:.1f}%)")
                            ocr_pages += 1
                        else:
                            page_text = f"[OCR ATTEMPTED - NO TEXT FOUND]"

                    except Exception as ocr_error:
                        page_text = f"[OCR ERROR: {str(ocr_error)}]"
                        st.warning(
                            f"OCR failed on page {page_num + 1}: {str(ocr_error)}")

                # Check if we got any meaningful text from this page
                if page_text.strip() and len(page_text.strip()) > 10:
                    text_content += page_text
                    text_content += f"\n\n--- End of Page {page_num + 1} ---\n\n"
                    pages_with_text += 1
                else:
                    text_content += f"\n--- Page {page_num + 1} (No text found) ---\n"
                    pages_without_text += 1

                # Update progress bar
                if progress_bar:
                    progress_bar.progress((page_num + 1) / page_count)

            except Exception as page_error:
                st.warning(
                    f"Error processing page {page_num + 1}: {str(page_error)}")
                text_content += f"\n--- Page {page_num + 1} (Error: {str(page_error)}) ---\n"
                pages_without_text += 1

        # Clear progress bar
        if progress_bar:
            progress_bar.empty()

        pdf_document.close()

        # Show extraction summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pages with Text", pages_with_text)
        with col2:
            st.metric("Pages without Text", pages_without_text)
        with col3:
            st.metric("OCR Pages", ocr_pages)
        with col4:
            st.metric("Languages", len(selected_languages))

        # Check if we extracted any meaningful text
        if not text_content.strip() or len(text_content.strip()) < 50:
            if not use_ocr:
                st.warning(
                    "⚠️ No text was extracted from the PDF using regular extraction.")
                st.info("This appears to be a scanned PDF or image-based PDF.")
                st.info(
                    "🔄 Try enabling OCR with appropriate Indic language support.")
                return None
            else:
                st.error("No text could be extracted even with OCR.")
                return None

        return text_content

    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None


def create_indic_word_document(text, encoding, font_name='Nirmala UI'):
    """Create a Word document with Indic font support"""
    doc = Document()

    # Set Indic font
    set_indic_font_in_docx(doc, font_name)

    # Add title
    title = doc.add_heading('Extracted PDF Text with Indic Support', 0)
    title_run = title.runs[0]
    title_run.font.name = font_name

    # Add metadata
    meta_para = doc.add_paragraph(f'Encoding: {encoding} | Font: {font_name}')
    meta_run = meta_para.runs[0]
    meta_run.font.name = font_name

    doc.add_paragraph('')

    # Split text into paragraphs and apply Indic font
    paragraphs = text.split('\n')
    for para_text in paragraphs:
        if para_text.strip():
            para = doc.add_paragraph(para_text)
            for run in para.runs:
                run.font.name = font_name

    return doc


def main():
    st.title("📄 PDF Text Extractor with Enhanced Indic Support")
    st.markdown(
        "Upload a PDF file to extract text with advanced Indic language and font support.")

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to extract text from"
    )

    if uploaded_file is not None:
        st.success(
            f"File uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")

        # Advanced OCR configuration
        st.subheader("🔧 OCR Configuration")

        col1, col2 = st.columns(2)

        with col1:
            # OCR enable/disable
            use_ocr = st.checkbox(
                "🔍 Enable Enhanced Indic OCR",
                help="Use advanced OCR with Indic language support for scanned documents"
            )

            # Preprocessing option
            enable_preprocessing = st.checkbox(
                "🎯 Enable Image Preprocessing",
                value=True,
                help="Apply specialized preprocessing for better Indic text recognition"
            )

        with col2:
            # Language selection
            selected_languages = st.multiselect(
                "Select Languages for OCR:",
                options=list(INDIC_LANGUAGES.keys()),
                default=['hindi', 'english'],
                help="Choose languages present in your document"
            )

            # Font selection for output
            font_options = ['Nirmala UI', 'Mangal', 'Sanskrit 2003',
                            'Kokila', 'Aparajita', 'Arial Unicode MS']
            selected_font = st.selectbox(
                "Select Output Font:",
                options=font_options,
                index=0,
                help="Choose font for Word document output (Indic-compatible fonts recommended)"
            )

        if use_ocr and not selected_languages:
            st.warning("Please select at least one language for OCR.")
            return

        if use_ocr:
            st.info("📋 Selected OCR Configuration:")
            st.write(f"• Languages: {', '.join(selected_languages)}")
            st.write(f"• Font: {selected_font}")
            st.write(
                f"• Preprocessing: {'Enabled' if enable_preprocessing else 'Disabled'}")
            st.warning(
                "⏱️ Enhanced Indic OCR may take longer but provides better accuracy for Indian language texts.")

        # Extract text
        if st.button("🚀 Extract Text", type="primary"):
            extraction_method = "Enhanced Indic OCR" if use_ocr else "Regular text extraction"
            with st.spinner(f"{extraction_method} in progress..."):
                extracted_text = extract_text_from_pdf(
                    uploaded_file,
                    use_ocr=use_ocr,
                    selected_languages=selected_languages,
                    enable_preprocessing=enable_preprocessing,
                    selected_font=selected_font
                )

            if extracted_text:
                # Display basic stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Characters", len(extracted_text))
                with col2:
                    st.metric("Words", len(extracted_text.split()))
                with col3:
                    st.metric("Lines", len(extracted_text.split('\n')))

                # Text preview
                st.subheader("📖 Text Preview")
                preview_text = extracted_text[:2000]
                if len(extracted_text) > 2000:
                    preview_text += "\n\n... (truncated for preview)"

                st.text_area(
                    f"Extracted text preview:",
                    preview_text,
                    height=400,
                    help="Preview of extracted text with Indic language support"
                )

                # Download section
                st.subheader("⬇️ Download Options")
                filename_base = uploaded_file.name.rsplit('.', 1)[0]

                col1, col2 = st.columns(2)

                with col1:
                    # Text file download
                    st.download_button(
                        label=f"📄 Download as TXT ({selected_font})",
                        data=extracted_text.encode('utf-8'),
                        file_name=f"{filename_base}_indic.txt",
                        mime='text/plain',
                        help=f"Download as UTF-8 text file optimized for {selected_font}"
                    )

                with col2:
                    # Word document with Indic font
                    doc = create_indic_word_document(
                        extracted_text, 'utf-8', selected_font)
                    doc_io = io.BytesIO()
                    doc.save(doc_io)
                    doc_io.seek(0)

                    st.download_button(
                        label=f"📝 Download as Word ({selected_font})",
                        data=doc_io.getvalue(),
                        file_name=f"{filename_base}_indic_{selected_font.replace(' ', '_')}.docx",
                        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        help=f"Download as Word document with {selected_font} font for proper Indic text display"
                    )

            else:
                st.error("Failed to extract text from the PDF file.")

    # Enhanced instructions sidebar
    with st.sidebar:
        st.header("ℹ️ How to Use")
        st.markdown("""
        1. **Upload PDF**: Choose your PDF file
        2. **Configure OCR**: 
           - Enable Enhanced Indic OCR for scanned documents
           - Select appropriate languages
           - Choose Indic-compatible font
        3. **Enable Preprocessing**: For better OCR accuracy
        4. **Extract Text**: Click the extract button
        5. **Download**: Get files with proper Indic font support
        """)

        st.header("🔤 Supported Languages")
        st.markdown("""
        **Indian Languages:**
        - Hindi (हिंदी)
        - Sanskrit (संस्कृत)
        - Bengali (বাংলা)
        - Gujarati (ગુજરાતી)
        - Kannada (ಕನ್ನಡ)
        - Malayalam (മലയാളം)
        - Marathi (मराठी)
        - Punjabi (ਪੰਜਾਬੀ)
        - Tamil (தமிழ்)
        - Telugu (తెలుగు)
        - Urdu (اردو)
        
        **Other:**
        - English
        """)

        st.header("🎨 Recommended Fonts")
        st.markdown("""
        **For Devanagari (Hindi/Sanskrit):**
        - Nirmala UI (Best overall)
        - Mangal (Windows default)
        - Sanskrit 2003
        - Kokila
        
        **For other scripts:**
        - Nirmala UI (Universal Indic)
        - Script-specific fonts available
        """)

        st.header("💡 Tips for Best Results")
        st.markdown("""
        - Use **Nirmala UI** for best Indic compatibility
        - Enable **preprocessing** for scanned documents
        - Select **multiple languages** if document is multilingual
        - For old/poor quality scans, try different font options
        - High-resolution scans work better with OCR
        """)


if __name__ == "__main__":
    main()
