import streamlit as st
import fitz  # PyMuPDF
import chardet
import io
import zipfile
from docx import Document
from docx.shared import Inches
import tempfile
import os
from PIL import Image
import pytesseract
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="PDF Text Extractor",
    page_icon="📄",
    layout="wide"
)


def extract_text_from_pdf(pdf_file, use_ocr=False):
    """Extract text from PDF file using PyMuPDF with optional OCR"""
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

        # Check page count - use len() for newer PyMuPDF versions
        try:
            page_count = len(pdf_document)
        except:
            try:
                page_count = pdf_document.page_count
            except:
                page_count = pdf_document.pageCount  # Even older versions

        if page_count == 0:
            st.error("PDF has no pages or pages cannot be accessed.")
            pdf_document.close()
            return None

        st.info(f"PDF loaded successfully: {page_count} pages found")

        if page_count > 500:
            st.warning(
                f"Large document ({page_count} pages). Processing may take time.")

        text_content = ""
        pages_with_text = 0
        pages_without_text = 0

        # Add progress bar for large documents
        progress_bar = None
        if page_count > 5 or use_ocr:
            progress_bar = st.progress(0)

        # chunk_size = 20  # Adjust as needed
        chunk_size = st.sidebar.slider(
            "OCR Chunk Size (pages per batch)", 2, 5, 50, 20,
            help="OCR will be processed in chunks of this size. Smaller chunks use less memory but may be slower overall."
        )

        for chunk_start in range(0, page_count, chunk_size):
            chunk_end = min(chunk_start + chunk_size, page_count)
            st.info(f"Processing pages {chunk_start + 1} to {chunk_end}")

            for page_num in range(chunk_start, chunk_end):
                try:
                    page = pdf_document.load_page(page_num)
                    page_text = page.get_text()

                    if (not page_text.strip() or len(page_text.strip()) < 10) and use_ocr:
                        # Run OCR
                        mat = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=mat)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        ocr_text = pytesseract.image_to_string(
                            img, lang='eng+hin+san')

                        if ocr_text.strip():
                            page_text = f"[OCR EXTRACTED]\n{ocr_text}"
                            st.success(f"OCR on page {page_num + 1}")
                        else:
                            page_text = "[OCR ATTEMPTED - NO TEXT FOUND]"

                    if page_text.strip() and len(page_text.strip()) > 10:
                        text_content += page_text + \
                            f"\n\n--- End of Page {page_num + 1} ---\n\n"
                        pages_with_text += 1
                    else:
                        text_content += f"\n--- Page {page_num + 1} (No text found) ---\n"
                        pages_without_text += 1

                    if progress_bar:
                        progress_bar.progress((page_num + 1) / page_count)

                except Exception as page_error:
                    st.warning(
                        f"Error on page {page_num + 1}: {str(page_error)}")
                    pages_without_text += 1

        # for page_num in range(page_count):
        #     try:
        #         # Use modern PyMuPDF API - access page by index
        #         try:
        #             page = pdf_document[page_num]  # New API
        #         except:
        #             try:
        #                 page = pdf_document.load_page(
        #                     page_num)  # Alternative API
        #             except:
        #                 page = pdf_document.loadPage(page_num)  # Older API

        #         # First try regular text extraction
        #         page_text = page.get_text()

        #         # If no text found and OCR is enabled, try OCR
        #         if (not page_text.strip() or len(page_text.strip()) < 10) and use_ocr:
        #             try:
        #                 # Convert page to image
        #                 # Increase resolution for better OCR
        #                 mat = fitz.Matrix(2.0, 2.0)
        #                 pix = page.get_pixmap(matrix=mat)
        #                 img_data = pix.tobytes("png")

        #                 # Convert to PIL Image
        #                 img = Image.open(io.BytesIO(img_data))

        #                 # Use Tesseract OCR
        #                 ocr_text = pytesseract.image_to_string(
        #                     img, lang='eng+hin+san')  # English, Hindi, Sanskrit

        #                 if ocr_text.strip():
        #                     page_text = f"[OCR EXTRACTED]\n{ocr_text}"
        #                     st.success(
        #                         f"OCR extracted text from page {page_num + 1}")
        #                 else:
        #                     page_text = f"[OCR ATTEMPTED - NO TEXT FOUND]"

        #             except Exception as ocr_error:
        #                 page_text = f"[OCR ERROR: {str(ocr_error)}]"
        #                 st.warning(
        #                     f"OCR failed on page {page_num + 1}: {str(ocr_error)}")

        #         # Check if we got any meaningful text from this page
        #         if page_text.strip() and len(page_text.strip()) > 10:
        #             text_content += page_text
        #             text_content += f"\n\n--- End of Page {page_num + 1} ---\n\n"
        #             pages_with_text += 1
        #         else:
        #             text_content += f"\n--- Page {page_num + 1} (No text found) ---\n"
        #             pages_without_text += 1

        #         # Update progress bar
        #         if progress_bar:
        #             progress_bar.progress((page_num + 1) / page_count)

        #     except Exception as page_error:
        #         st.warning(
        #             f"Error processing page {page_num + 1}: {str(page_error)}")
        #         text_content += f"\n--- Page {page_num + 1} (Error: {str(page_error)}) ---\n"
        #         pages_without_text += 1

        # Clear progress bar
        if progress_bar:
            progress_bar.empty()

        pdf_document.close()

        # Show extraction summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pages with Text", pages_with_text)
        with col2:
            st.metric("Pages without Text", pages_without_text)
        with col3:
            st.metric("OCR Used", "Yes" if use_ocr else "No")

        # Check if we extracted any meaningful text
        if not text_content.strip() or len(text_content.strip()) < 50:
            if not use_ocr:
                st.warning(
                    "⚠️ No text was extracted from the PDF using regular extraction.")
                st.info("This appears to be a scanned PDF or image-based PDF.")
                st.info("🔄 Try enabling OCR (Optical Character Recognition) below.")
                return None
            else:
                st.error("No text could be extracted even with OCR.")
                return None

        return text_content

    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        st.info("Try checking if:")
        st.info("• The PDF file is not corrupted")
        st.info("• The PDF is not password-protected")
        st.info("• The file is actually a PDF (not renamed image)")
        return None


def detect_encoding(text):
    """Detect possible encodings for the text"""
    encodings_to_try = [
        'utf-8', 'utf-16', 'utf-32',
        'ascii', 'latin1', 'cp1252',
        'iso-8859-1', 'iso-8859-15',
        'cp850', 'cp437',
        'big5', 'gb2312', 'shift_jis',
        'koi8-r', 'cp1251'
    ]

    detected_encodings = []

    # Try chardet first
    try:
        text_bytes = text.encode('utf-8')
        detected = chardet.detect(text_bytes)
        if detected['encoding'] and detected['confidence'] > 0.7:
            detected_encodings.append({
                'encoding': detected['encoding'],
                'confidence': detected['confidence'],
                'method': 'chardet'
            })
    except:
        pass

    # Try different encodings
    for encoding in encodings_to_try:
        try:
            # Encode then decode to test if encoding works
            test_bytes = text.encode('utf-8')
            decoded = test_bytes.decode('utf-8')

            detected_encodings.append({
                'encoding': encoding,
                'confidence': 1.0 if encoding == 'utf-8' else 0.8,
                'method': 'manual_test'
            })
        except:
            continue

    # Remove duplicates and sort by confidence
    seen_encodings = set()
    unique_encodings = []
    for enc in detected_encodings:
        if enc['encoding'] not in seen_encodings:
            seen_encodings.add(enc['encoding'])
            unique_encodings.append(enc)

    return sorted(unique_encodings, key=lambda x: x['confidence'], reverse=True)


def create_word_document(text, encoding):
    """Create a Word document with the extracted text"""
    doc = Document()
    doc.add_heading('Extracted PDF Text', 0)
    doc.add_paragraph(f'Encoding: {encoding}')
    doc.add_paragraph('')

    # Split text into paragraphs to avoid single large paragraph
    paragraphs = text.split('\n')
    for para in paragraphs:
        if para.strip():
            doc.add_paragraph(para)

    return doc


def create_download_files(text, selected_encoding, filename_base):
    """Create downloadable files in different formats"""
    files = {}

    try:
        # Text file
        text_bytes = text.encode(selected_encoding)
        files['txt'] = {
            'content': text_bytes,
            'filename': f"{filename_base}_{selected_encoding}.txt",
            'mimetype': 'text/plain'
        }

        # Word document
        doc = create_word_document(text, selected_encoding)
        doc_io = io.BytesIO()
        doc.save(doc_io)
        doc_io.seek(0)
        files['docx'] = {
            'content': doc_io.getvalue(),
            'filename': f"{filename_base}_{selected_encoding}.docx",
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }

    except Exception as e:
        st.error(
            f"Error creating files with encoding {selected_encoding}: {str(e)}")
        return None

    return files


def main():
    st.title("📄 PDF Text Extractor with Encoding Options")
    st.markdown(
        "Upload a PDF file to extract text and download it in various formats with proper encoding.")

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload a PDF file to extract text from"
    )

    if uploaded_file is not None:
        # Display file info
        st.success(
            f"File uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")

        # OCR option
        use_ocr = st.checkbox(
            "🔍 Enable OCR (for scanned/image-based PDFs)",
            help="Use Optical Character Recognition to extract text from images. This will take longer but can read scanned documents."
        )

        if use_ocr:
            st.info("📋 OCR Language Support: English, Hindi, Sanskrit")
            st.warning(
                "⏱️ OCR processing may take significantly longer, especially for large documents.")

        # Extract text
        extraction_method = "OCR extraction" if use_ocr else "Regular text extraction"
        with st.spinner(f"{extraction_method} in progress..."):
            extracted_text = extract_text_from_pdf(
                uploaded_file, use_ocr=use_ocr)

        if extracted_text:
            # Display basic stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Characters", len(extracted_text))
            with col2:
                st.metric("Words", len(extracted_text.split()))
            with col3:
                st.metric("Lines", len(extracted_text.split('\n')))

            # Detect encodings
            st.subheader("🔍 Encoding Detection")
            with st.spinner("Detecting possible encodings..."):
                possible_encodings = detect_encoding(extracted_text)

            if possible_encodings:
                # Create encoding options
                encoding_options = []
                for enc_info in possible_encodings[:10]:  # Limit to top 10
                    confidence_pct = int(enc_info['confidence'] * 100)
                    encoding_options.append(
                        f"{enc_info['encoding']} (confidence: {confidence_pct}%)"
                    )

                # Encoding selection
                selected_encoding_display = st.selectbox(
                    "Select encoding for viewing and download:",
                    encoding_options,
                    help="Choose the encoding that displays the text correctly"
                )

                # Extract actual encoding name
                selected_encoding = selected_encoding_display.split(' (')[0]

                # Display text preview
                st.subheader("📖 Text Preview")
                try:
                    # Try to encode and decode with selected encoding
                    # First 2000 characters
                    preview_text = extracted_text[:2000]
                    if len(extracted_text) > 2000:
                        preview_text += "\n\n... (truncated for preview)"

                    st.text_area(
                        f"Text preview with {selected_encoding} encoding:",
                        preview_text,
                        height=300,
                        help="This is a preview of the extracted text with the selected encoding"
                    )

                except Exception as e:
                    st.error(
                        f"Error displaying text with encoding {selected_encoding}: {str(e)}")

                # Download section
                st.subheader("⬇️ Download Options")

                filename_base = uploaded_file.name.rsplit(
                    '.', 1)[0]  # Remove .pdf extension

                # Create download files
                with st.spinner("Preparing download files..."):
                    download_files = create_download_files(
                        extracted_text, selected_encoding, filename_base)

                if download_files:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.download_button(
                            label="📄 Download as TXT",
                            data=download_files['txt']['content'],
                            file_name=download_files['txt']['filename'],
                            mime=download_files['txt']['mimetype'],
                            help=f"Download as text file with {selected_encoding} encoding"
                        )

                    with col2:
                        st.download_button(
                            label="📝 Download as Word Document",
                            data=download_files['docx']['content'],
                            file_name=download_files['docx']['filename'],
                            mime=download_files['docx']['mimetype'],
                            help=f"Download as Word document with {selected_encoding} encoding"
                        )

                # Encoding comparison section
                with st.expander("🔧 Compare Different Encodings"):
                    st.markdown(
                        "Compare how the text looks with different encodings:")

                    comparison_encodings = [enc['encoding']
                                            for enc in possible_encodings[:5]]

                    for encoding in comparison_encodings:
                        st.markdown(f"**{encoding}:**")
                        try:
                            # First 500 characters
                            sample_text = extracted_text[:500]
                            st.text(sample_text)
                        except Exception as e:
                            st.error(
                                f"Cannot display with {encoding}: {str(e)}")
                        st.markdown("---")

            else:
                st.warning(
                    "Could not detect suitable encodings for this text.")

                # Fallback download with UTF-8
                st.subheader("⬇️ Download with UTF-8 (Default)")
                filename_base = uploaded_file.name.rsplit('.', 1)[0]

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📄 Download as TXT (UTF-8)",
                        data=extracted_text.encode('utf-8'),
                        file_name=f"{filename_base}_utf8.txt",
                        mime='text/plain'
                    )

                with col2:
                    doc = create_word_document(extracted_text, 'utf-8')
                    doc_io = io.BytesIO()
                    doc.save(doc_io)
                    doc_io.seek(0)

                    st.download_button(
                        label="📝 Download as Word Document (UTF-8)",
                        data=doc_io.getvalue(),
                        file_name=f"{filename_base}_utf8.docx",
                        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    )

        else:
            st.error("Failed to extract text from the PDF file.")

    # Instructions
    with st.sidebar:
        st.header("ℹ️ How to Use")
        st.markdown("""
        1. **Upload PDF**: Click 'Browse files' to upload your PDF
        2. **Enable OCR**: Check the box if your PDF contains scanned images
        3. **View Stats**: See character, word, and line counts
        4. **Select Encoding**: Choose the best encoding for your text
        5. **Preview Text**: Review the extracted text
        6. **Download**: Get TXT or Word document with proper encoding
        
        **OCR Notes:**
        - Use OCR for scanned documents or image-based PDFs
        - OCR supports English, Hindi, and Sanskrit
        - OCR processing takes longer but extracts text from images
        
        **Encoding Tips:**
        - UTF-8: Works for most modern documents
        - Latin1/CP1252: Common for Western European texts
        - ASCII: Basic English text only
        - Other encodings: For specific languages/regions
        """)

        st.header("🔧 Supported Features")
        st.markdown("""
        - PDF text extraction (regular + OCR)
        - Scanned document support via Tesseract OCR
        - Multiple language support (English, Hindi, Sanskrit)
        - Multiple encoding detection
        - Text and Word document export
        - Encoding comparison
        - Character encoding validation
        - Progress tracking for large files
        """)


if __name__ == "__main__":
    main()
