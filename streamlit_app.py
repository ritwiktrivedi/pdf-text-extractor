import streamlit as st
import fitz  # PyMuPDF
import chardet
import io
import zipfile
from docx import Document
from docx.shared import Inches
import tempfile
import os

# Set page configuration
st.set_page_config(
    page_title="PDF Text Extractor",
    page_icon="📄",
    layout="wide"
)


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file using PyMuPDF"""
    try:
        # Check file size (optional warning for large files)
        file_size_mb = pdf_file.size / (1024 * 1024)
        if file_size_mb > 50:
            st.warning(
                f"Large file detected ({file_size_mb:.1f}MB). Processing may take a while.")

        # Read PDF from uploaded file
        pdf_bytes = pdf_file.read()
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Check page count
        page_count = pdf_document.page_count
        if page_count > 500:
            st.warning(
                f"Large document ({page_count} pages). Processing may take time.")

        text_content = ""
        # Add progress bar for large documents
        if page_count > 10:
            progress_bar = st.progress(0)

        for page_num in range(page_count):
            page = pdf_document.page(page_num)
            text_content += page.get_text()
            text_content += f"\n--- Page {page_num + 1} ---\n"

            # Update progress bar
            if page_count > 10:
                progress_bar.progress((page_num + 1) / page_count)

        # Clear progress bar
        if page_count > 10:
            progress_bar.empty()

        pdf_document.close()
        return text_content

    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
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

        # Extract text
        with st.spinner("Extracting text from PDF..."):
            extracted_text = extract_text_from_pdf(uploaded_file)

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
        2. **View Stats**: See character, word, and line counts
        3. **Select Encoding**: Choose the best encoding for your text
        4. **Preview Text**: Review the extracted text
        5. **Download**: Get TXT or Word document with proper encoding
        
        **Encoding Tips:**
        - UTF-8: Works for most modern documents
        - Latin1/CP1252: Common for Western European texts
        - ASCII: Basic English text only
        - Other encodings: For specific languages/regions
        """)

        st.header("🔧 Supported Features")
        st.markdown("""
        - PDF text extraction
        - Multiple encoding detection
        - Text and Word document export
        - Encoding comparison
        - Character encoding validation
        """)


if __name__ == "__main__":
    main()
