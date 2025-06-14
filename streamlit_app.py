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
import google.generativeai as genai
import base64
from typing import List, Dict, Optional, Tuple
import time
import logging

# Set page configuration
st.set_page_config(
    page_title="Advanced PDF Text Extractor with AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
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


def setup_gemini(api_key: str) -> bool:
    """Setup Gemini API with user's API key"""
    try:
        genai.configure(api_key=api_key)
        # Test the API key with a simple request
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        test_response = model.generate_content("Test connection")
        return True
    except Exception as e:
        st.error(f"Failed to setup Gemini API: {str(e)}")
        return False


def extract_text_with_gemini(image: Image.Image, selected_languages: List[str],
                             extraction_type: str = "general") -> Tuple[str, float]:
    """Extract text using Google Gemini 2.0 Flash Vision with enhanced prompts"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Create language-specific prompt
        language_names = {
            'hindi': 'Hindi (हिंदी)', 'sanskrit': 'Sanskrit (संस्कृत)',
            'bengali': 'Bengali (বাংলা)', 'gujarati': 'Gujarati (ગુજરાતી)',
            'kannada': 'Kannada (ಕನ್ನಡ)', 'malayalam': 'Malayalam (മലയാളം)',
            'marathi': 'Marathi (मराठी)', 'punjabi': 'Punjabi (ਪੰਜਾਬੀ)',
            'tamil': 'Tamil (தமிழ்)', 'telugu': 'Telugu (తెలుగు)',
            'urdu': 'Urdu (اردو)', 'english': 'English'
        }

        selected_lang_names = [language_names.get(
            lang, lang) for lang in selected_languages]

        if extraction_type == "academic":
            prompt = f"""You are an expert in extracting text from academic documents. Please extract ALL text from this image with the following requirements:

1. **Languages Expected**: {', '.join(selected_lang_names)}
2. **Preserve Format**: Maintain original formatting, line breaks, and structure
3. **Handle Mixed Scripts**: The document may contain multiple languages/scripts
4. **Academic Content**: Pay special attention to:
   - Mathematical formulas and equations
   - Citations and references
   - Technical terminology
   - Footnotes and annotations
   - Tables and structured data
   - Headers and subheadings

5. **Quality Requirements**:
   - Extract every visible character with maximum accuracy
   - Maintain proper spacing and punctuation
   - Preserve paragraph breaks and indentation
   - Keep original text order and layout
   - Handle complex formatting like subscripts/superscripts

Please provide the extracted text exactly as it appears in the image, preserving all formatting and structure. If there are any mathematical symbols, formulas, or special characters, include them accurately."""

        elif extraction_type == "indic_specialized":
            prompt = f"""You are a specialist in Indian languages and scripts with deep expertise in historical and cultural texts. Please extract ALL text from this image with expertise in:

1. **Target Languages**: {', '.join(selected_lang_names)}
2. **Script Recognition**: Expert knowledge of:
   - Devanagari (देवनागरी) - including complex conjuncts
   - Bengali script (বাংলা লিপি) - with proper matras
   - Tamil script (தமிழ் எழுத்து) - including Tamil numerals
   - Telugu script (తెలుగు లిపి) - with conjunct consonants
   - Other Indian scripts with their unique characteristics

3. **Cultural Context**: Understanding of:
   - Religious texts and Sanskrit terminology
   - Historical documents and manuscripts
   - Classical literature and poetry
   - Traditional naming conventions
   - Regional variations in script styles

4. **Technical Accuracy**:
   - Correct diacritical marks (anusvara, visarga, etc.)
   - Proper conjunct consonants and ligatures
   - Accurate vowel marks (matras)
   - Context-aware word boundaries
   - Proper handling of numerals and dates

Extract every character with perfect accuracy, maintaining the cultural and linguistic integrity of the text. Pay special attention to archaic forms and historical spelling variations."""

        elif extraction_type == "handwritten":
            prompt = f"""You are an expert in recognizing handwritten text in multiple scripts. Please extract ALL text from this handwritten document with the following expertise:

1. **Languages Expected**: {', '.join(selected_lang_names)}
2. **Handwriting Recognition**: Specialized in:
   - Cursive and print handwriting styles
   - Individual writing variations
   - Faded or unclear characters
   - Mixed script documents

3. **Quality Focus**:
   - Distinguish between similar-looking characters
   - Handle unclear or partially visible text
   - Make educated guesses for ambiguous characters
   - Maintain reading flow and context

Extract all visible text, indicating any uncertain characters with [?] if needed."""

        else:  # general
            prompt = f"""Please extract ALL text from this image with maximum accuracy. The text may be in the following languages: {', '.join(selected_lang_names)}.

Requirements:
1. Extract every visible character and word with perfect accuracy
2. Maintain original formatting, line breaks, and spacing
3. Preserve the natural reading order (left-to-right, right-to-left as appropriate)
4. Handle mixed languages and scripts appropriately
5. Include all punctuation, numbers, and special characters
6. Preserve headers, footers, and any metadata visible
7. Maintain table structures if present

Provide the complete extracted text exactly as it appears in the image, with no summarization or interpretation - just pure text extraction."""

        # Convert image to bytes for Gemini
        img_byte_arr = io.BytesIO()
        # Ensure high quality for better text recognition
        image.save(img_byte_arr, format='PNG', optimize=False, quality=100)
        img_byte_arr.seek(0)

        # Generate content with timeout handling
        try:
            response = model.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,  # Low temperature for more consistent results
                    top_p=0.8,
                    max_output_tokens=8192,
                )
            )

            extracted_text = response.text if response.text else ""

        except Exception as api_error:
            st.error(f"Gemini API call failed: {str(api_error)}")
            return "", 0

        # Estimate confidence based on response quality and characteristics
        confidence = 95.0  # Gemini typically provides high quality results

        # Adjust confidence based on text characteristics
        if len(extracted_text.strip()) < 10:
            confidence = 40.0
        elif not any(char.isalpha() for char in extracted_text):
            confidence = 60.0
        elif len(extracted_text.strip()) < 50:
            confidence = 75.0
        elif any(lang in ['hindi', 'sanskrit', 'bengali', 'tamil'] for lang in selected_languages):
            # Boost confidence for Indic languages as Gemini handles them well
            confidence = min(98.0, confidence + 5.0)

        return extracted_text, confidence

    except Exception as e:
        st.error(f"Gemini extraction failed: {str(e)}")
        return "", 0


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
            if any(lang in ['bengali'] for lang in selected_languages):
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


def extract_text_from_pdf(pdf_file, extraction_method="regular", selected_languages=['hindi', 'english'],
                          enable_preprocessing=True, selected_font='Nirmala UI', gemini_extraction_type="general"):
    """Extract text from PDF file using multiple methods"""
    try:
        # Check file size first
        file_size_mb = pdf_file.size / (1024 * 1024)

        if pdf_file.size < 100:
            st.error(
                f"File is too small ({pdf_file.size} bytes) to be a valid PDF.")
            return None

        if file_size_mb > 50:
            st.warning(
                f"Large file detected ({file_size_mb:.1f}MB). Processing may take a while.")

        # Read PDF from uploaded file
        pdf_bytes = pdf_file.read()

        if not pdf_bytes.startswith(b'%PDF'):
            st.error("This doesn't appear to be a valid PDF file.")
            return None

        # Try to open the PDF
        try:
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as pdf_error:
            st.error(f"Cannot open PDF file: {str(pdf_error)}")
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

        st.info(f"📄 PDF loaded successfully: {page_count} pages found")
        st.info(f"🎯 Extraction Method: {extraction_method.title()}")
        st.info(f"🌐 Languages: {', '.join(selected_languages)}")

        if page_count > 500:
            st.warning(
                f"⚠️ Large document ({page_count} pages). Processing may take significant time.")

        text_content = ""
        pages_with_text = 0
        pages_without_text = 0
        extraction_stats = {"regular": 0, "tesseract": 0, "gemini": 0}

        # Add progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        for page_num in range(page_count):
            try:
                status_text.text(
                    f"Processing page {page_num + 1}/{page_count}...")

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
                extraction_used = "regular"

                # If no meaningful text found, try advanced methods
                if not page_text.strip() or len(page_text.strip()) < 10:
                    # Convert page to image for advanced extraction
                    # High resolution for better AI recognition
                    mat = fitz.Matrix(3.0, 3.0)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))

                    if extraction_method == "gemini":
                        # Use Gemini for extraction
                        gemini_text, confidence = extract_text_with_gemini(
                            img, selected_languages, gemini_extraction_type)

                        if gemini_text.strip():
                            page_text = f"[GEMINI EXTRACTED - Confidence: {confidence:.1f}%]\n{gemini_text}"
                            extraction_used = "gemini"
                            st.success(
                                f"✨ Gemini extracted text from page {page_num + 1} (Confidence: {confidence:.1f}%)")

                    elif extraction_method == "tesseract_ocr":
                        # Use Tesseract OCR
                        ocr_text, confidence = extract_text_with_indic_ocr(
                            img, selected_languages, enable_preprocessing)

                        if ocr_text.strip():
                            page_text = f"[TESSERACT OCR - Confidence: {confidence:.1f}%]\n{ocr_text}"
                            extraction_used = "tesseract"
                            st.success(
                                f"🔍 Tesseract extracted text from page {page_num + 1} (Confidence: {confidence:.1f}%)")

                    elif extraction_method == "hybrid":
                        # Try both methods and use the better result
                        gemini_text, gemini_conf = extract_text_with_gemini(
                            img, selected_languages, gemini_extraction_type)

                        time.sleep(0.5)  # Rate limiting for Gemini

                        ocr_text, ocr_conf = extract_text_with_indic_ocr(
                            img, selected_languages, enable_preprocessing)

                        # Choose better result based on confidence and length
                        if gemini_conf > ocr_conf or len(gemini_text) > len(ocr_text) * 1.2:
                            if gemini_text.strip():
                                page_text = f"[HYBRID: GEMINI SELECTED - Confidence: {gemini_conf:.1f}%]\n{gemini_text}"
                                extraction_used = "gemini"
                                st.success(
                                    f"✨ Hybrid: Gemini selected for page {page_num + 1} (Conf: {gemini_conf:.1f}%)")
                        else:
                            if ocr_text.strip():
                                page_text = f"[HYBRID: TESSERACT SELECTED - Confidence: {ocr_conf:.1f}%]\n{ocr_text}"
                                extraction_used = "tesseract"
                                st.success(
                                    f"🔍 Hybrid: Tesseract selected for page {page_num + 1} (Conf: {ocr_conf:.1f}%)")

                # Count extraction statistics
                extraction_stats[extraction_used] += 1

                # Check if we got meaningful text
                if page_text.strip() and len(page_text.strip()) > 10:
                    text_content += page_text
                    text_content += f"\n\n--- End of Page {page_num + 1} ({extraction_used.title()}) ---\n\n"
                    pages_with_text += 1
                else:
                    text_content += f"\n--- Page {page_num + 1} (No text found) ---\n"
                    pages_without_text += 1

                # Update progress
                progress_bar.progress((page_num + 1) / page_count)

                # Rate limiting for Gemini API
                if extraction_method in ["gemini", "hybrid"]:
                    # Slightly increased delay for API stability
                    time.sleep(0.2)

            except Exception as page_error:
                st.warning(
                    f"⚠️ Error processing page {page_num + 1}: {str(page_error)}")
                text_content += f"\n--- Page {page_num + 1} (Error: {str(page_error)}) ---\n"
                pages_without_text += 1

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        pdf_document.close()

        # Show extraction summary
        st.subheader("📊 Extraction Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pages with Text", pages_with_text,
                      delta=f"{(pages_with_text/page_count)*100:.1f}%")
        with col2:
            st.metric("Pages without Text", pages_without_text)
        with col3:
            st.metric("Total Languages", len(selected_languages))
        with col4:
            st.metric("Primary Method", extraction_method.title())

        # Show extraction method breakdown
        if any(count > 0 for count in extraction_stats.values()):
            st.subheader("🔍 Extraction Method Breakdown")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Regular Text", extraction_stats["regular"],
                          help="Direct text extraction from PDF")
            with col2:
                st.metric("Tesseract OCR", extraction_stats["tesseract"],
                          help="OCR-based text recognition")
            with col3:
                st.metric("Gemini AI", extraction_stats["gemini"],
                          help="AI-powered text extraction")

        # Check if we extracted meaningful text
        if not text_content.strip() or len(text_content.strip()) < 50:
            st.error("❌ No meaningful text could be extracted from the PDF.")
            st.info(
                "💡 Try switching to a different extraction method or check if the PDF contains text/images.")
            return None

        return text_content

    except Exception as e:
        st.error(f"❌ Error extracting text from PDF: {str(e)}")
        return None


def create_indic_word_document(text, encoding, font_name='Nirmala UI'):
    """Create a Word document with Indic font support"""
    doc = Document()

    # Set Indic font
    set_indic_font_in_docx(doc, font_name)

    # Add title
    title = doc.add_heading('Extracted PDF Text with Advanced AI Support', 0)
    title_run = title.runs[0]
    title_run.font.name = font_name

    # Add metadata
    meta_para = doc.add_paragraph(
        f'Encoding: {encoding} | Font: {font_name} | Extracted on: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    meta_run = meta_para.runs[0]
    meta_run.font.name = font_name
    meta_run.font.size = Inches(0.15)

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
    st.title("🚀 Advanced PDF Text Extractor with AI")
    st.markdown("""
    **Extract text from PDFs using cutting-edge AI technology:**
    - 🤖 **Google Gemini 2.0 Flash** for superior text recognition
    - 🔍 **Tesseract OCR** with Indic language support
    - 🌐 **12+ Indian languages** supported
    - 📄 **Multiple output formats** (TXT, DOCX)
    """)

    # API Key Input
    st.sidebar.header("🔑 API Configuration")

    with st.sidebar.expander("🤖 Google Gemini API Setup", expanded=True):
        st.markdown("""
        **Get your free API key:**
        1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
        2. Sign in with your Google account
        3. Click "Create API Key"
        4. Copy and paste it below
        
        **🔒 Privacy Note**: This is an open-source project. Your API key is only used during your session and is never stored or logged.
        """)

        gemini_api_key = st.text_input(
            "Google Gemini API Key",
            type="password",
            help="Your API key is secure and only used for this session",
            placeholder="Enter your Gemini API key here..."
        )

        if gemini_api_key:
            with st.spinner("Verifying API key..."):
                if setup_gemini(gemini_api_key):
                    st.success("✅ Gemini API configured successfully!")
                    st.balloons()
                else:
                    st.error("❌ Invalid API key or connection failed")
                    st.info("Please check your API key and internet connection")

    # File upload
    st.header("📁 Upload Your PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file to extract text from",
        type=['pdf'],
        help="Upload any PDF file - text-based, scanned, or image-based documents supported"
    )

    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.success(
            f"✅ File uploaded: **{uploaded_file.name}** ({file_size_mb:.2f} MB)")

        # Extraction method selection
        st.header("🎯 Extraction Configuration")

        col1, col2 = st.columns(2)

        with col1:
            extraction_methods = {
                "regular": "🔤 Regular Text Extraction",
                "tesseract_ocr": "🔍 Tesseract OCR Only",
                "gemini": "✨ Google Gemini AI Only",
                "hybrid": "🚀 Hybrid (Gemini + Tesseract)"
            }

            default_method = 3 if gemini_api_key else 1
            extraction_method = st.selectbox(
                "Select Extraction Method:",
                options=list(extraction_methods.keys()),
                format_func=lambda x: extraction_methods[x],
                index=default_method,
                help="Choose the extraction method based on your document type"
            )

            # Disable AI methods if no API key
            if extraction_method in ["gemini", "hybrid"] and not gemini_api_key:
                st.error("🔑 Gemini API key required for AI extraction methods")
                st.stop()

        with col2:
            # Language selection
            selected_languages = st.multiselect(
                "Select Languages in Your Document:",
                options=list(INDIC_LANGUAGES.keys()),
                default=['hindi', 'english'],
                help="Choose all languages present in your document for better accuracy"
            )

        # Advanced options
        with st.expander("🔧 Advanced Configuration"):
            col1, col2, col3 = st.columns(3)

            with col1:
                enable_preprocessing = st.checkbox(
                    "📐 Enable Image Preprocessing",
                    value=True,
                    help="Apply specialized preprocessing for better text recognition (recommended)"
                )

            with col2:
                gemini_extraction_types = {
                    "general": "📄 General Text Extraction",
                    "academic": "🎓 Academic Documents",
                    "indic_specialized": "🕉️ Indic Language Specialist",
                    "handwritten": "✍️ Handwritten Text"
                }

                gemini_extraction_type = st.selectbox(
                    "Gemini Extraction Mode:",
                    options=list(gemini_extraction_types.keys()),
                    format_func=lambda x: gemini_extraction_types[x],
                    help="Choose specialized extraction mode for optimal results"
                )

            with col3:
                font_options = ['Nirmala UI', 'Mangal', 'Sanskrit 2003',
                                'Kokila', 'Aparajita', 'Arial Unicode MS']
                selected_font = st.selectbox(
                    "Output Font for Word Document:",
                    options=font_options,
                    index=0,
                    help="Choose font that best supports your document's languages"
                )

        # Method descriptions and recommendations
        method_descriptions = {
            "regular": "🔤 **Regular Extraction**: Fast direct text extraction from text-based PDFs. Best for: Digital documents, eBooks, modern PDFs.",
            "tesseract_ocr": "🔍 **Tesseract OCR**: Advanced OCR with Indic language support. Best for: Scanned documents, older PDFs, mixed-script content.",
            "gemini": "✨ **Gemini AI**: State-of-the-art AI text recognition. Best for: Complex layouts, handwritten text, challenging documents.",
            "hybrid": "🚀 **Hybrid Method**: Combines Gemini AI and Tesseract, automatically selects the best result. Best for: Maximum accuracy across all document types."
        }

        st.info(method_descriptions[extraction_method])

        if not selected_languages:
            st.warning("⚠️ Please select at least one language to proceed.")
            st.stop()

        # Extract text
        if st.button("🚀 Start Text Extraction", type="primary", use_container_width=True):
            with st.spinner("🔄 Processing your PDF... This may take a few moments."):
                try:
                    extracted_text = extract_text_from_pdf(
                        uploaded_file,
                        extraction_method=extraction_method,
                        selected_languages=selected_languages,
                        enable_preprocessing=enable_preprocessing,
                        selected_font=selected_font,
                        gemini_extraction_type=gemini_extraction_type
                    )

                    if extracted_text:
                        st.success("🎉 Text extraction completed successfully!")

                        # Display extracted text
                        st.header("📝 Extracted Text")

                        # Text preview with expandable section
                        preview_length = 500
                        if len(extracted_text) > preview_length:
                            st.text_area(
                                "Text Preview (First 500 characters):",
                                extracted_text[:preview_length] + "...",
                                height=150,
                                disabled=True
                            )

                            with st.expander("📖 View Full Extracted Text", expanded=False):
                                st.text_area(
                                    "Complete Extracted Text:",
                                    extracted_text,
                                    height=400,
                                    disabled=True
                                )
                        else:
                            st.text_area(
                                "Extracted Text:",
                                extracted_text,
                                height=300,
                                disabled=True
                            )

                        # Text statistics
                        st.subheader("📊 Text Statistics")
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric("Total Characters", len(extracted_text))
                        with col2:
                            word_count = len(extracted_text.split())
                            st.metric("Word Count", word_count)
                        with col3:
                            line_count = len(extracted_text.split('\n'))
                            st.metric("Lines", line_count)
                        with col4:
                            # Estimate reading time (average 200 words per minute)
                            reading_time = max(1, word_count // 200)
                            st.metric("Est. Reading Time",
                                      f"{reading_time} min")

                        # Download options
                        st.header("💾 Download Options")

                        col1, col2 = st.columns(2)

                        with col1:
                            # Download as TXT
                            txt_download = st.download_button(
                                label="📄 Download as TXT",
                                data=extracted_text.encode('utf-8'),
                                file_name=f"extracted_text_{uploaded_file.name.replace('.pdf', '')}.txt",
                                mime="text/plain",
                                help="Download the extracted text as a plain text file"
                            )

                        with col2:
                            # Download as DOCX
                            try:
                                # Detect encoding
                                detected_encoding = chardet.detect(
                                    extracted_text.encode())['encoding']
                                if not detected_encoding:
                                    detected_encoding = 'utf-8'

                                # Create Word document
                                doc = create_indic_word_document(
                                    extracted_text, detected_encoding, selected_font)

                                # Save to bytes
                                doc_buffer = io.BytesIO()
                                doc.save(doc_buffer)
                                doc_buffer.seek(0)

                                docx_download = st.download_button(
                                    label="📝 Download as DOCX",
                                    data=doc_buffer.getvalue(),
                                    file_name=f"extracted_text_{uploaded_file.name.replace('.pdf', '')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    help="Download as a formatted Word document with Indic font support"
                                )

                            except Exception as doc_error:
                                st.error(
                                    f"❌ Error creating Word document: {str(doc_error)}")
                                st.info(
                                    "💡 You can still download the text as a TXT file above.")

                        # Additional features
                        st.header("🔍 Additional Features")

                        with st.expander("🔎 Text Search & Analysis"):
                            search_term = st.text_input(
                                "Search in extracted text:", placeholder="Enter search term...")

                            if search_term:
                                # Case-insensitive search
                                search_results = []
                                lines = extracted_text.split('\n')

                                for i, line in enumerate(lines):
                                    if search_term.lower() in line.lower():
                                        search_results.append(
                                            (i+1, line.strip()))

                                if search_results:
                                    st.success(
                                        f"Found {len(search_results)} occurrences of '{search_term}':")

                                    # Show first 10 results
                                    for line_num, line_text in search_results[:10]:
                                        # Highlight search term
                                        highlighted_line = line_text.replace(
                                            search_term,
                                            f"**{search_term}**"
                                        )
                                        st.write(
                                            f"**Line {line_num}:** {highlighted_line}")

                                    if len(search_results) > 10:
                                        st.info(
                                            f"... and {len(search_results) - 10} more results")
                                else:
                                    st.warning(
                                        f"No occurrences of '{search_term}' found.")

                        with st.expander("📈 Language Analysis"):
                            # Simple language detection based on character sets
                            language_stats = {}

                            for lang in selected_languages:
                                if lang == 'english':
                                    # Count English characters (basic ASCII)
                                    eng_chars = sum(
                                        1 for c in extracted_text if c.isascii() and c.isalpha())
                                    language_stats['English'] = eng_chars
                                elif lang == 'hindi':
                                    # Count Devanagari characters
                                    hindi_chars = sum(
                                        1 for c in extracted_text if '\u0900' <= c <= '\u097F')
                                    language_stats['Hindi'] = hindi_chars
                                elif lang == 'bengali':
                                    # Count Bengali characters
                                    bengali_chars = sum(
                                        1 for c in extracted_text if '\u0980' <= c <= '\u09FF')
                                    language_stats['Bengali'] = bengali_chars
                                # Add more language character counting as needed

                            if language_stats:
                                st.write(
                                    "**Character distribution by script:**")
                                for lang, count in language_stats.items():
                                    if count > 0:
                                        percentage = (
                                            count / len(extracted_text)) * 100
                                        st.write(
                                            f"- {lang}: {count} characters ({percentage:.1f}%)")

                        # Success message with tips
                        st.success(
                            "✅ **Extraction Complete!** Your text has been successfully extracted and is ready for download.")

                        st.info("""
                        💡 **Tips for better results:**
                        - For scanned documents, try the **Hybrid** method for best accuracy
                        - Select all languages present in your document
                        - Use **Academic** mode for research papers and technical documents
                        - Enable preprocessing for better OCR quality on unclear images
                        """)

                    else:
                        st.error(
                            "❌ Failed to extract text from the PDF. Please try a different extraction method or check if the PDF contains extractable content.")

                        st.info("""
                        🔧 **Troubleshooting suggestions:**
                        - Try switching to **Hybrid** or **Gemini** extraction method
                        - Ensure your PDF contains text or clear images
                        - Check if the document is password-protected
                        - For handwritten documents, use **Handwritten** mode in Gemini settings
                        """)

                except Exception as e:
                    st.error(
                        f"❌ An error occurred during text extraction: {str(e)}")
                    st.info(
                        "Please try again with a different extraction method or contact support if the issue persists.")

                    # Log error for debugging (in production, use proper logging)
                    logging.error(f"Text extraction error: {str(e)}")

    else:
        # Show example and instructions when no file is uploaded
        st.header("🎯 How to Use This Tool")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("1️⃣ Upload PDF")
            st.write(
                "Upload any PDF file - text-based, scanned, or image-based documents are all supported.")

        with col2:
            st.subheader("2️⃣ Configure Settings")
            st.write(
                "Choose extraction method, select languages, and configure advanced options as needed.")

        with col3:
            st.subheader("3️⃣ Extract & Download")
            st.write(
                "Get your extracted text in multiple formats with detailed statistics and search capabilities.")

        st.header("🌟 Key Features")

        features = [
            "🤖 **AI-Powered Extraction**: Google Gemini 2.0 Flash for superior accuracy",
            "🔍 **Advanced OCR**: Tesseract with specialized Indic language support",
            "🌐 **Multi-Language**: Support for 12+ Indian languages plus English",
            "🚀 **Hybrid Mode**: Combines multiple extraction methods for best results",
            "📄 **Multiple Formats**: Download as TXT or formatted DOCX files",
            "🔎 **Text Search**: Built-in search and analysis tools",
            "📊 **Detailed Stats**: Word count, reading time, and language analysis",
            "🔒 **Privacy First**: Your API key and documents are never stored"
        ]

        for feature in features:
            st.markdown(feature)

        st.header("📋 Supported Document Types")

        doc_types = {
            "✅ **Text-based PDFs**": "Digital documents, eBooks, reports",
            "✅ **Scanned Documents**": "Scanned papers, old documents, photocopies",
            "✅ **Mixed Content**": "Documents with both text and images",
            "✅ **Multi-language**": "Documents in multiple scripts and languages",
            "✅ **Academic Papers**": "Research papers, technical documents",
            "✅ **Handwritten Text**": "Handwritten notes and documents (with Gemini AI)"
        }

        for doc_type, description in doc_types.items():
            st.write(f"{doc_type}: {description}")


# Run the application
if __name__ == "__main__":
    main()
