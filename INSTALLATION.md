# Installation Guide for OCR Functionality

This guide will walk you through setting up Tesseract OCR and TR-OCR (Transformer OCR) for the document/image analysis feature of IntelliLearn.

## Installing Tesseract OCR

Tesseract OCR is required for basic OCR functionality. Follow these instructions based on your operating system:

### Windows

1. Download the Tesseract installer from the official GitHub repository: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer and select the languages you want to install (at minimum, select English)
3. Make sure to remember the installation path (e.g., `C:\Program Files\Tesseract-OCR`)
4. Set the environment variable:
   - Right-click on "This PC" or "My Computer" and select "Properties"
   - Click on "Advanced system settings"
   - Click "Environment Variables"
   - Under "System variables", click "New"
   - Add a variable named `TESSERACT_PATH` with the value of your installation path (e.g., `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### macOS

1. Install via Homebrew:
   ```
   brew install tesseract
   ```
2. Set the environment variable in your shell profile (e.g., .bash_profile, .zshrc):
   ```
   export TESSERACT_PATH=/usr/local/bin/tesseract
   ```

### Linux (Ubuntu/Debian)

1. Install via apt:
   ```
   sudo apt update
   sudo apt install tesseract-ocr
   ```
2. Set the environment variable in your shell profile:
   ```
   export TESSERACT_PATH=/usr/bin/tesseract
   ```

## Installing TR-OCR (optional, for better handwriting recognition)

TR-OCR is a transformer-based OCR system that provides improved recognition for handwritten text.

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Installation Steps

1. Install PyTorch:
   ```
   pip install torch torchvision
   ```

2. Install Transformers library:
   ```
   pip install transformers
   ```

3. Verify installation:
   - The system will automatically use TR-OCR if both libraries are installed correctly
   - You can select between Tesseract (faster, better for printed text) and TR-OCR (better for handwritten text) in the interface

## Troubleshooting

### Tesseract Not Found

If you encounter errors about Tesseract not being found:

1. Ensure Tesseract is properly installed
2. Double-check that the `TESSERACT_PATH` environment variable is set correctly
3. Restart your application server

### TR-OCR Not Loading

If TR-OCR doesn't work:

1. Verify that PyTorch and Transformers are installed:
   ```
   pip list | grep torch
   pip list | grep transformers
   ```

2. Check for any error messages in the console/logs

3. Ensure you have sufficient disk space (the model is several GB)

## Additional Language Support

To add support for languages other than English in Tesseract OCR:

### Windows

- Run the installer again and select additional languages

### macOS

```
brew install tesseract-lang
```

### Linux

```
sudo apt install tesseract-ocr-all
```

or for specific languages:

```
sudo apt install tesseract-ocr-[lang]
```
Replace [lang] with the language code (e.g., fra for French, deu for German) 