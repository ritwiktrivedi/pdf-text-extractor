# 🚀 Enhanced PDF Text Extractor with AI

A powerful, AI-enhanced PDF text extraction tool built with Streamlit that supports multiple languages, especially Indic languages, with advanced OCR capabilities and Google Gemini AI integration.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🚀 Super Quick Start

Use deployed version on streamlit:
https://pdf-multilang-text-extractor.streamlit.app/

# Not that below doc is under development

Corrections and additions via PRs welcome.

## ✨ Features

### 🎯 **Multiple Extraction Methods**

- **Hybrid Mode**: Combines regular PDF text extraction with AI-powered OCR
- **Gemini AI Only**: Advanced AI-powered text extraction using Google Gemini
- **Enhanced OCR**: Tesseract-based OCR with image preprocessing
- **Regular PDF**: Standard PDF text extraction

### 🌐 **Multi-Language Support**

Supports 12+ languages including:

- English, Sanskrit, Hindi, Bengali, Telugu, Tamil
- Marathi, Gujarati, Punjabi, Kannada
- Malayalam, Urdu + possibly more with Gemini Image Understanding (AI Mode).

### 🤖 **AI-Powered Features**

- **Google Gemini Integration**: Advanced AI text extraction
- **Document Type Recognition**: Academic, General, Indic-specialized, Handwritten
- **Confidence Scoring**: Quality assessment for extracted text
- **Smart Batch Processing**: Efficient handling of large documents

### 📊 **Advanced Processing**

- **Batch Processing**: Configurable batch sizes for optimal performance
- **Image Preprocessing**: Enhancement for better OCR accuracy
- **Progress Tracking**: Real-time processing status
- **Memory Management**: Efficient resource utilization

### 💾 **Multiple Export Formats**

- **TXT**: Plain text format
- **DOCX**: Rich text with metadata

### 🔄 **Persistent State Management**

- Results remain available after processing
- Multiple downloads without re-processing
- Clear state management for new files

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Tesseract OCR installed on your system
- Google Gemini API key (for AI features)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/ritwiktrivedi/pdf-text-extractor.git
cd pdf-text-extractor
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Install Tesseract OCR**

**Ubuntu/Debian:**

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng tesseract-ocr-san
```

**macOS:**

```bash
brew install tesseract tesseract-lang
```

(Need to confirm this.... Please test and make PR to this open source initiative)

4. **Run the application**

```bash
streamlit run app.py
```

## 📖 Usage

### Basic Usage

1. **Upload PDF**: Choose your PDF file using the file uploader
2. **Configure Settings**: Select extraction method, languages, and options
3. **Add AI Key**: Enter your Gemini API key for AI-powered extraction
4. **Start Extraction**: Click the extraction button and monitor progress
5. **Download Results**: Download in your preferred format (TXT, DOCX, JSON)

### Configuration Options

#### Extraction Methods

- **Hybrid (Recommended)**: Best accuracy, combines multiple techniques
- **Gemini AI Only**: Pure AI extraction, great for complex documents
- **Enhanced OCR**: Traditional OCR with preprocessing
- **Regular PDF**: Fast, for text-based PDFs

#### Language Selection

Choose from 12+ supported languages. Multiple languages can be selected for multilingual documents.

#### Processing Options

- **Batch Size**: 1-20 pages per batch (default: 5)
- **Max Pages**: Limit processing for large documents
- **Preprocessing**: Enable image enhancement for better OCR
- **Debug Mode**: Detailed processing information

## 🔧 Configuration

### Environment Setup

Create a `.env` file (optional) or export to environment or add to .bashrc in WSL:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### API Keys

- **Google Gemini API**: Required for AI-powered extraction
- Get your key from: https://aistudio.google.com/apikey

## 📁 Project Structure

```
enhanced-pdf-extractor/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── packages.txt           # OCR packages
```

## 🛠️ Requirements

### Python Packages

```txt
streamlit>=1.28.0
PyMuPDF>=1.23.0
pytesseract>=0.3.10
Pillow>=10.0.0
google-generativeai>=0.3.0
python-docx>=0.8.11
pandas>=2.0.0
numpy>=1.24.0
opencv-python>=4.8.0
python-dotenv>=1.0.0
```

### System Dependencies

- **Tesseract OCR** with language packs
- **Python 3.8+**
- **At least 4GB RAM** (recommended for large PDFs)

## 🎯 Performance Tips

### For Best Results:

1. **Use Hybrid Mode** for most documents
2. **Enable Preprocessing** for scanned documents
3. **Select Appropriate Languages** for your content
4. **Adjust Batch Size** based on your system (lower for limited RAM)
5. **Use Gemini AI** for complex layouts or handwritten text

### Memory Management:

- Large PDFs are processed in configurable batches
- Automatic memory cleanup after processing
- Progress tracking prevents browser timeouts

## 🔍 Troubleshooting

### Common Issues

**1. Tesseract Not Found**

```bash
# Linux/Mac
which tesseract
# Update path in app.py if needed

# Windows
# Install from official source and add to PATH
```

**2. Gemini API Errors**

- Verify API key is correct
- Check API quota/billing
- Ensure stable internet connection

**3. Memory Issues**

- Reduce batch size
- Process fewer pages at once
- Close other applications

**4. Poor OCR Quality**

- Enable image preprocessing
- Try different extraction methods
- Ensure good PDF quality

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📊 Supported Document Types

- **Academic Papers**: Research documents, journals
- **Business Documents**: Reports, presentations
- **Scanned Documents**: Image-based PDFs
- **Multilingual Content**: Mixed language documents
- **Handwritten Text**: With Gemini AI extraction
- **Complex Layouts**: Tables, columns, mixed content

## 🌟 Advanced Features

### Batch Processing

- Configurable batch sizes
- Progress tracking
- Memory optimization
- Error recovery

### AI Integration

- Google Gemini Pro integration
- Document type recognition
- Confidence scoring
- Quality assessment

### Export Options

- Rich DOCX with metadata
- Plain text with encoding options
- JSON with extraction details
- Debug information export

## 📈 Roadmap

- [ ] **Azure OpenAI Integration**
- [ ] **PDF Form Field Extraction**
- [ ] **Table Structure Recognition**
- [ ] **API Endpoint Version**
- [ ] **Docker Containerization**
- [ ] **Batch File Processing**
- [ ] **Custom Model Training**

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Streamlit** for the amazing web framework
- **Google Gemini** for AI capabilities
- **Tesseract OCR** for text recognition
- **PyMuPDF** for PDF processing
- **OpenCV** for image preprocessing

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ritwiktrivedi/pdf-text-extractor/issues)

## ⭐ Star History

If you find this project helpful, please consider giving it a star! ⭐

---

**Made with ❤️ and AI for the open source community**
