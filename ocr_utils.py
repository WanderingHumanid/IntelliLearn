import os
import pytesseract
from PIL import Image
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to tesseract executable - users need to set this in their environment
# Default paths:
# Windows: 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
# Mac: '/usr/local/bin/tesseract'
# Linux: '/usr/bin/tesseract'
TESSERACT_PATH = os.environ.get('TESSERACT_PATH', '')
if not TESSERACT_PATH:
    # Set default paths based on operating system
    if os.name == 'nt':  # Windows
        default_path = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        if os.path.exists(default_path):
            TESSERACT_PATH = default_path
            logger.info(f"Using default Windows Tesseract path: {TESSERACT_PATH}")

if TESSERACT_PATH:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    logger.info(f"Tesseract path set to: {TESSERACT_PATH}")
else:
    logger.warning("Tesseract path not set! OCR functionality may be limited.")

# Flag to indicate if TR-OCR is available
TR_OCR_AVAILABLE = False
TR_OCR_MODEL = None
TR_OCR_PROCESSOR = None
DEVICE = None

# Try to import torch and transformers
try:
    import torch
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    
    # TR-OCR model
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    TR_OCR_AVAILABLE = True
    
except ImportError:
    logger.warning("PyTorch or Transformers not available. TR-OCR functionality will be disabled.")

def load_tr_ocr_model():
    """Load the TR-OCR model"""
    global TR_OCR_MODEL, TR_OCR_PROCESSOR, TR_OCR_AVAILABLE
    
    if not TR_OCR_AVAILABLE:
        logger.warning("TR-OCR is not available. Please install torch and transformers.")
        return False
    
    try:
        if TR_OCR_MODEL is None:
            logger.info("Loading TR-OCR model...")
            # Set specific version for compatibility
            model_name = "microsoft/trocr-base-handwritten"
            
            try:
                # Use more compatible approach
                config = {
                    "pretrained_model_name_or_path": model_name,
                    "revision": "main",
                    "use_auth_token": None,
                    "trust_remote_code": False,
                    "local_files_only": False,
                    "cache_dir": None
                }
                import torch.nn as nn
                
                # Use direct class instantiation instead of init_empty_weights
                TR_OCR_PROCESSOR = TrOCRProcessor.from_pretrained(model_name, **config)
                TR_OCR_MODEL = VisionEncoderDecoderModel.from_pretrained(model_name, **config)
                TR_OCR_MODEL.to(DEVICE)
                logger.info("TR-OCR model loaded successfully.")
            except AttributeError as ae:
                logger.error(f"Error loading TR-OCR model: {ae}")
                TR_OCR_AVAILABLE = False
                return False
            except Exception as e:
                logger.error(f"General error loading TR-OCR model: {e}")
                TR_OCR_AVAILABLE = False
                return False
    except Exception as e:
        logger.error(f"Error loading TR-OCR model: {e}")
        TR_OCR_AVAILABLE = False
        return False
    
    return True

def perform_tesseract_ocr(image_path):
    """Perform OCR using Tesseract"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Tesseract OCR error: {e}")
        return f"Error performing OCR: {str(e)}"

def perform_tr_ocr(image_path):
    """Perform OCR using TR-OCR (Transformer OCR)"""
    if not TR_OCR_AVAILABLE:
        return "TR-OCR is not available. Using Tesseract OCR instead."
    
    if not load_tr_ocr_model():
        return "Failed to load TR-OCR model. Using Tesseract OCR instead."
    
    try:
        image = Image.open(image_path).convert("RGB")
        pixel_values = TR_OCR_PROCESSOR(image, return_tensors="pt").pixel_values.to(DEVICE)
        
        generated_ids = TR_OCR_MODEL.generate(pixel_values)
        generated_text = TR_OCR_PROCESSOR.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return generated_text.strip()
    except Exception as e:
        logger.error(f"TR-OCR error: {e}")
        return f"Error performing TR-OCR: {str(e)}"

def save_uploaded_file(file_object):
    """Save an uploaded file to a temporary location"""
    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_object.filename)[1])
        temp_file_path = temp_file.name
        temp_file.close()
        
        # Save the uploaded file to the temporary location
        file_object.save(temp_file_path)
        return temp_file_path
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        return None

def extract_text_from_image(file_path, use_tr_ocr=True):
    """Extract text from an image using either Tesseract or TR-OCR"""
    result = ""
    
    # First try with the selected OCR method
    if use_tr_ocr and TR_OCR_AVAILABLE:
        try:
            logger.info("Attempting TR-OCR")
            tr_ocr_result = perform_tr_ocr(file_path)
            if tr_ocr_result and not tr_ocr_result.startswith("Error") and not tr_ocr_result.startswith("Failed") and not tr_ocr_result.startswith("TR-OCR"):
                return tr_ocr_result
        except Exception as e:
            logger.error(f"TR-OCR failed, falling back to Tesseract: {e}")
    
    # Fall back to Tesseract if TR-OCR fails or wasn't selected
    logger.info("Falling back to Tesseract OCR")
    try:
        tesseract_result = perform_tesseract_ocr(file_path)
        if tesseract_result and not tesseract_result.startswith("Error"):
            return tesseract_result
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {e}")
    
    # If both methods fail, return a generic message
    return "Failed to extract text from image" 