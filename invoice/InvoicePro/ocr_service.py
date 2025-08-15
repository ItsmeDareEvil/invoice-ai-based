import os
import cv2
import pytesseract
import json
import logging
from PIL import Image
import numpy as np
from typing import Dict, Any, List
import re
from datetime import datetime
import openai

class OCRDocumentProcessor:
    """Advanced OCR processing for invoices and receipts"""
    
    def __init__(self):
        self.tesseract_cmd = self._find_tesseract()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        
        # Configure OpenAI for intelligent text processing
        openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    def _find_tesseract(self) -> str:
        """Find Tesseract executable on different systems"""
        common_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
            'tesseract'
        ]
        
        for path in common_paths:
            if os.path.exists(path) or self._is_command_available(path):
                return path
        
        logging.warning("Tesseract not found. OCR functionality will be limited.")
        return None
    
    def _is_command_available(self, command: str) -> bool:
        """Check if command is available in system PATH"""
        try:
            os.system(f"{command} --version > /dev/null 2>&1")
            return True
        except:
            return False
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Deskew the image
            coords = np.column_stack(np.where(thresh > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5:  # Only rotate if significant skew
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                thresh = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            # Apply morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return thresh
            
        except Exception as e:
            logging.error(f"Image preprocessing failed: {e}")
            # Return original image if preprocessing fails
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            if not self.tesseract_cmd:
                return "OCR not available - Tesseract not found"
            
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Configure OCR parameters
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/() '
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip()
            
        except Exception as e:
            logging.error(f"OCR text extraction failed: {e}")
            return f"OCR failed: {str(e)}"
    
    def extract_invoice_data(self, image_path: str) -> Dict[str, Any]:
        """Extract structured invoice data from scanned document"""
        try:
            # Extract raw text
            raw_text = self.extract_text_from_image(image_path)
            
            if not raw_text or "OCR failed" in raw_text:
                return {"error": "OCR extraction failed", "raw_text": raw_text}
            
            # Use AI to structure the extracted text
            structured_data = self._ai_parse_invoice_text(raw_text)
            
            # Add confidence scores and validation
            structured_data["ocr_confidence"] = self._calculate_confidence_score(raw_text)
            structured_data["raw_text"] = raw_text
            structured_data["needs_manual_review"] = structured_data["ocr_confidence"] < 0.7
            
            return structured_data
            
        except Exception as e:
            logging.error(f"Invoice data extraction failed: {e}")
            return {"error": str(e)}
    
    def _ai_parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Use AI to parse and structure invoice text"""
        try:
            prompt = f"""
            Parse the following OCR-extracted invoice text and return structured data in JSON format:
            
            OCR Text:
            {text}
            
            Extract and return the following information in JSON format:
            {{
                "invoice_number": "extracted invoice number",
                "invoice_date": "YYYY-MM-DD format",
                "due_date": "YYYY-MM-DD format if found",
                "vendor_info": {{
                    "name": "vendor/company name",
                    "address": "vendor address",
                    "phone": "phone number",
                    "email": "email address",
                    "gst_number": "GST/tax number"
                }},
                "client_info": {{
                    "name": "client/customer name",
                    "address": "client address"
                }},
                "line_items": [
                    {{
                        "description": "item description",
                        "quantity": float,
                        "unit_price": float,
                        "total_amount": float
                    }}
                ],
                "totals": {{
                    "subtotal": float,
                    "tax_amount": float,
                    "total_amount": float
                }},
                "payment_info": {{
                    "payment_terms": "payment terms if found",
                    "bank_details": "bank details if found"
                }},
                "extracted_fields_confidence": {{
                    "invoice_number": float between 0-1,
                    "amounts": float between 0-1,
                    "dates": float between 0-1,
                    "contact_info": float between 0-1
                }}
            }}
            
            If any field cannot be extracted, use null or empty string. Be conservative with confidence scores.
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            parsed_data = json.loads(response.choices[0].message.content)
            return parsed_data
            
        except Exception as e:
            logging.error(f"AI invoice parsing failed: {e}")
            return self._fallback_parse_invoice_text(text)
    
    def _fallback_parse_invoice_text(self, text: str) -> Dict[str, Any]:
        """Fallback parsing using regex patterns"""
        try:
            parsed_data = {
                "invoice_number": self._extract_invoice_number(text),
                "invoice_date": self._extract_date(text, "invoice"),
                "due_date": self._extract_date(text, "due"),
                "total_amount": self._extract_total_amount(text),
                "vendor_info": {},
                "client_info": {},
                "line_items": [],
                "totals": {},
                "payment_info": {},
                "extracted_fields_confidence": {
                    "invoice_number": 0.5,
                    "amounts": 0.4,
                    "dates": 0.4,
                    "contact_info": 0.3
                }
            }
            
            return parsed_data
            
        except Exception as e:
            logging.error(f"Fallback parsing failed: {e}")
            return {"error": str(e)}
    
    def _extract_invoice_number(self, text: str) -> str:
        """Extract invoice number using regex patterns"""
        patterns = [
            r'(?i)invoice\s*(?:no|number|#)\s*:?\s*([A-Z0-9\-/]+)',
            r'(?i)inv\s*(?:no|#)\s*:?\s*([A-Z0-9\-/]+)',
            r'(?i)bill\s*(?:no|number|#)\s*:?\s*([A-Z0-9\-/]+)',
            r'(?i)reference\s*(?:no|number|#)\s*:?\s*([A-Z0-9\-/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_date(self, text: str, date_type: str) -> str:
        """Extract dates from text"""
        patterns = [
            r'(?i)' + date_type + r'\s*(?:date)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)' + date_type + r'\s*(?:date)?\s*:?\s*(\d{1,2}\s+\w+\s+\d{2,4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    # Try to parse and format the date
                    parsed_date = self._parse_date_string(date_str)
                    return parsed_date.strftime("%Y-%m-%d")
                except:
                    continue
        
        return ""
    
    def _parse_date_string(self, date_str: str) -> datetime:
        """Parse date string in various formats"""
        formats = [
            "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
            "%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d",
            "%d %B %Y", "%d %b %Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse date: {date_str}")
    
    def _extract_total_amount(self, text: str) -> float:
        """Extract total amount from text"""
        patterns = [
            r'(?i)total\s*:?\s*(?:rs|₹|inr)?\s*([0-9,]+\.?\d*)',
            r'(?i)grand\s*total\s*:?\s*(?:rs|₹|inr)?\s*([0-9,]+\.?\d*)',
            r'(?i)amount\s*(?:due|payable)?\s*:?\s*(?:rs|₹|inr)?\s*([0-9,]+\.?\d*)',
            r'(?:rs|₹|inr)\s*([0-9,]+\.?\d*)',
            r'([0-9,]+\.\d{2})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Get the largest amount found (likely the total)
                amounts = []
                for match in matches:
                    try:
                        amount = float(match.replace(',', ''))
                        amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    return max(amounts)
        
        return 0.0
    
    def _calculate_confidence_score(self, text: str) -> float:
        """Calculate confidence score based on text quality and completeness"""
        try:
            score = 0.0
            
            # Check for common invoice elements
            if re.search(r'(?i)invoice', text):
                score += 0.2
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text):
                score += 0.2
            if re.search(r'(?:rs|₹|inr|\$)\s*\d+', text):
                score += 0.2
            if re.search(r'(?i)total', text):
                score += 0.2
            
            # Check text quality
            word_count = len(text.split())
            if word_count > 50:
                score += 0.1
            if word_count > 100:
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception:
            return 0.3

class ExpenseReceiptProcessor(OCRDocumentProcessor):
    """Specialized processor for expense receipts"""
    
    def extract_receipt_data(self, image_path: str) -> Dict[str, Any]:
        """Extract expense data from receipt"""
        try:
            # Extract text using parent class method
            raw_text = self.extract_text_from_image(image_path)
            
            if not raw_text or "OCR failed" in raw_text:
                return {"error": "OCR extraction failed", "raw_text": raw_text}
            
            # Use AI for intelligent categorization
            receipt_data = self._ai_categorize_expense(raw_text)
            receipt_data["raw_text"] = raw_text
            receipt_data["processing_date"] = datetime.utcnow().isoformat()
            
            return receipt_data
            
        except Exception as e:
            logging.error(f"Receipt processing failed: {e}")
            return {"error": str(e)}
    
    def _ai_categorize_expense(self, text: str) -> Dict[str, Any]:
        """Use AI to categorize and extract expense information"""
        try:
            prompt = f"""
            Analyze the following receipt text and categorize the expense. Return structured data in JSON format:
            
            Receipt Text:
            {text}
            
            Return the following information in JSON format:
            {{
                "vendor_name": "merchant/vendor name",
                "expense_date": "YYYY-MM-DD format",
                "amount": float,
                "category": "primary expense category",
                "subcategory": "specific subcategory",
                "description": "brief description of the expense",
                "tax_amount": float,
                "business_purpose": "likely business purpose",
                "tax_deductible": boolean,
                "confidence_score": float between 0-1,
                "suggested_categories": ["list of possible categories"],
                "extracted_items": [
                    {{
                        "item": "item name",
                        "price": float
                    }}
                ],
                "payment_method": "cash/card/digital if detectable"
            }}
            
            Common expense categories: Office Supplies, Travel, Meals, Fuel, Utilities, Software, Hardware, Professional Services, Marketing, Training
            """
            
            response = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            categorized_data = json.loads(response.choices[0].message.content)
            return categorized_data
            
        except Exception as e:
            logging.error(f"AI expense categorization failed: {e}")
            return {"error": str(e)}

def initialize_ocr_service():
    """Initialize OCR services"""
    try:
        global ocr_processor, receipt_processor
        ocr_processor = OCRDocumentProcessor()
        receipt_processor = ExpenseReceiptProcessor()
        
        logging.info("OCR services initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize OCR services: {e}")
        return False

# Global OCR service instances
ocr_processor = None
receipt_processor = None
