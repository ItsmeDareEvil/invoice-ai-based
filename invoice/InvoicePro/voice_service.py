import json
import logging
import re
from typing import Dict, Any, Optional, List
import openai
from datetime import datetime, timedelta
from app import db
from models import Client, Invoice, InvoiceLineItem, AIInteraction

class VoiceCommandProcessor:
    """Process voice commands for invoice operations"""
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        
        # Define supported commands and their patterns
        self.command_patterns = {
            "create_invoice": [
                "create invoice", "new invoice", "make invoice", "generate invoice"
            ],
            "search_client": [
                "find client", "search client", "look for client", "get client"
            ],
            "search_invoice": [
                "find invoice", "search invoice", "look for invoice", "get invoice"
            ],
            "add_item": [
                "add item", "add product", "include item", "insert item"
            ],
            "get_summary": [
                "show summary", "get summary", "display summary", "summary"
            ],
            "payment_status": [
                "payment status", "check payment", "payment check"
            ],
            "calculate_total": [
                "calculate total", "total amount", "sum up", "calculate"
            ],
            "save_invoice": [
                "save invoice", "save this", "finish invoice", "complete invoice"
            ]
        }
    
    def process_voice_command(self, user_id: int, voice_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process voice command and return structured response"""
        try:
            # Clean and normalize the voice input
            cleaned_text = self._clean_voice_input(voice_text)
            
            # Detect command intent using AI
            intent_analysis = self._analyze_command_intent(cleaned_text, context)
            
            # Execute the command based on intent
            result = self._execute_command(user_id, intent_analysis, cleaned_text, context)
            
            # Log the interaction
            self._log_voice_interaction(user_id, voice_text, intent_analysis, result)
            
            return result
            
        except Exception as e:
            logging.error(f"Voice command processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Sorry, I couldn't process that command. Please try again."
            }
    
    def _clean_voice_input(self, text: str) -> str:
        """Clean and normalize voice input text"""
        # Remove common speech artifacts
        text = re.sub(r'\b(um|uh|er|ah)\b', '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Convert numbers written as words to digits where appropriate
        text = self._convert_words_to_numbers(text)
        
        return text
    
    def _convert_words_to_numbers(self, text: str) -> str:
        """Convert number words to digits"""
        word_to_num = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90', 'hundred': '100', 'thousand': '1000'
        }
        
        for word, num in word_to_num.items():
            text = re.sub(r'\b' + word + r'\b', num, text, flags=re.IGNORECASE)
        
        return text
    
    def _analyze_command_intent(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use AI to analyze command intent and extract entities"""
        try:
            context_info = json.dumps(context, default=str) if context else "No context"
            
            prompt = f"""
            Analyze the following voice command for invoice management and extract the intent and entities:
            
            Voice Command: "{text}"
            Current Context: {context_info}
            
            Determine the intent and extract relevant entities. Return JSON in this format:
            {{
                "intent": "primary intent (create_invoice, search_client, add_item, etc.)",
                "confidence": float between 0-1,
                "entities": {{
                    "client_name": "client name if mentioned",
                    "amount": float if amount mentioned,
                    "item_description": "item description if mentioned",
                    "quantity": float if quantity mentioned,
                    "date": "YYYY-MM-DD if date mentioned",
                    "invoice_number": "invoice number if mentioned",
                    "action_modifiers": ["urgent", "draft", "send", etc.]
                }},
                "parameters": {{
                    "requires_confirmation": boolean,
                    "missing_info": ["list of required info not provided"],
                    "suggested_follow_up": "suggested follow-up question"
                }},
                "alternative_intents": [
                    {{
                        "intent": "alternative intent",
                        "confidence": float
                    }}
                ]
            }}
            
            Common intents: create_invoice, search_client, search_invoice, add_item, update_item, 
            calculate_total, save_invoice, send_invoice, payment_status, client_summary, get_analytics
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            intent_data = json.loads(response.choices[0].message.content)
            return intent_data
            
        except Exception as e:
            logging.error(f"Intent analysis failed: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "parameters": {"requires_confirmation": True, "missing_info": ["intent unclear"]}
            }
    
    def _execute_command(self, user_id: int, intent_analysis: Dict[str, Any], 
                        original_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the identified command"""
        intent = intent_analysis.get("intent", "unknown")
        entities = intent_analysis.get("entities", {})
        
        # Route to specific command handlers
        if intent == "create_invoice":
            return self._handle_create_invoice(user_id, entities, context)
        elif intent == "search_client":
            return self._handle_search_client(entities)
        elif intent == "search_invoice":
            return self._handle_search_invoice(entities)
        elif intent == "add_item":
            return self._handle_add_item(entities, context)
        elif intent == "calculate_total":
            return self._handle_calculate_total(context)
        elif intent == "payment_status":
            return self._handle_payment_status(entities)
        elif intent == "client_summary":
            return self._handle_client_summary(entities)
        elif intent == "save_invoice":
            return self._handle_save_invoice(context)
        else:
            return self._handle_unknown_command(original_text, intent_analysis)
    
    def _handle_create_invoice(self, user_id: int, entities: Dict[str, Any], 
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle invoice creation command"""
        try:
            client_name = entities.get("client_name")
            
            if not client_name:
                return {
                    "success": False,
                    "message": "I need a client name to create an invoice. Please specify which client this invoice is for.",
                    "action_required": "provide_client_name",
                    "suggested_response": "Please say 'Create invoice for [client name]'"
                }
            
            # Search for client
            client = Client.query.filter(
                Client.name.ilike(f"%{client_name}%")
            ).first()
            
            if not client:
                # Suggest creating new client or finding similar clients
                similar_clients = Client.query.filter(
                    Client.name.ilike(f"%{client_name.split()[0]}%")
                ).limit(5).all()
                
                response = {
                    "success": False,
                    "message": f"I couldn't find a client named '{client_name}'.",
                    "action_required": "clarify_client"
                }
                
                if similar_clients:
                    response["similar_clients"] = [
                        {"id": c.id, "name": c.name} for c in similar_clients
                    ]
                    response["message"] += f" Did you mean one of these clients: {', '.join([c.name for c in similar_clients[:3]])}?"
                else:
                    response["message"] += " Would you like me to create a new client with this name?"
                    response["action_required"] = "create_new_client"
                
                return response
            
            # Create invoice context
            invoice_context = {
                "client_id": client.id,
                "client_name": client.name,
                "created_via_voice": True,
                "voice_command_user": user_id,
                "line_items": []
            }
            
            return {
                "success": True,
                "message": f"Started creating invoice for {client.name}. You can now add items by saying 'Add [item description] quantity [number] price [amount]'",
                "invoice_context": invoice_context,
                "next_steps": [
                    "Add line items",
                    "Set invoice date",
                    "Review and save"
                ]
            }
            
        except Exception as e:
            logging.error(f"Create invoice command failed: {e}")
            return {
                "success": False,
                "message": "I encountered an error while creating the invoice. Please try again.",
                "error": str(e)
            }
    
    def _handle_add_item(self, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle adding item to invoice"""
        try:
            description = entities.get("item_description")
            quantity = entities.get("quantity", 1)
            amount = entities.get("amount")
            
            if not description:
                return {
                    "success": False,
                    "message": "I need an item description. Please tell me what item you want to add.",
                    "action_required": "provide_item_description"
                }
            
            if not amount:
                return {
                    "success": False,
                    "message": f"I need the price for '{description}'. Please specify the amount.",
                    "action_required": "provide_price"
                }
            
            # Add item to context
            if not context:
                context = {"line_items": []}
            
            if "line_items" not in context:
                context["line_items"] = []
            
            new_item = {
                "description": description,
                "quantity": float(quantity),
                "unit_price": float(amount),
                "total_amount": float(quantity) * float(amount),
                "added_via_voice": True
            }
            
            context["line_items"].append(new_item)
            
            total_items = len(context["line_items"])
            current_total = sum(item["total_amount"] for item in context["line_items"])
            
            return {
                "success": True,
                "message": f"Added {description} (quantity: {quantity}, price: ₹{amount}) to the invoice. Current total: ₹{current_total:.2f}",
                "invoice_context": context,
                "summary": {
                    "total_items": total_items,
                    "current_total": current_total
                }
            }
            
        except Exception as e:
            logging.error(f"Add item command failed: {e}")
            return {
                "success": False,
                "message": "I couldn't add that item. Please check the description and price and try again.",
                "error": str(e)
            }
    
    def _handle_search_client(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle client search command"""
        try:
            client_name = entities.get("client_name")
            
            if not client_name:
                return {
                    "success": False,
                    "message": "Please specify which client you want to search for.",
                    "action_required": "provide_client_name"
                }
            
            # Search for clients
            clients = Client.query.filter(
                Client.name.ilike(f"%{client_name}%")
            ).limit(10).all()
            
            if not clients:
                return {
                    "success": False,
                    "message": f"No clients found matching '{client_name}'."
                }
            
            if len(clients) == 1:
                client = clients[0]
                recent_invoices_count = Invoice.query.filter_by(client_id=client.id).count()
                total_business = db.session.query(db.func.sum(Invoice.total_amount))\
                    .filter(Invoice.client_id == client.id, Invoice.payment_status == 'Paid').scalar() or 0
                
                return {
                    "success": True,
                    "message": f"Found {client.name}. They have {recent_invoices_count} invoices with total business of ₹{total_business:.2f}",
                    "client_data": {
                        "id": client.id,
                        "name": client.name,
                        "email": client.email,
                        "phone": client.phone,
                        "total_business": float(total_business),
                        "invoice_count": recent_invoices_count
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"Found {len(clients)} clients matching '{client_name}':",
                    "clients": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "email": c.email,
                            "phone": c.phone
                        }
                        for c in clients
                    ]
                }
                
        except Exception as e:
            logging.error(f"Search client command failed: {e}")
            return {
                "success": False,
                "message": "I couldn't search for clients right now. Please try again.",
                "error": str(e)
            }
    
    def _handle_calculate_total(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle total calculation command"""
        try:
            if not context or "line_items" not in context:
                return {
                    "success": False,
                    "message": "No items found to calculate total. Please add some items first."
                }
            
            line_items = context["line_items"]
            subtotal = sum(item["total_amount"] for item in line_items)
            
            # Calculate tax (assuming 18% GST)
            tax_rate = 0.18
            cgst = subtotal * (tax_rate / 2)
            sgst = subtotal * (tax_rate / 2)
            total_amount = subtotal + cgst + sgst
            
            return {
                "success": True,
                "message": f"Invoice total: Subtotal ₹{subtotal:.2f}, CGST ₹{cgst:.2f}, SGST ₹{sgst:.2f}, Total Amount ₹{total_amount:.2f}",
                "calculation": {
                    "subtotal": subtotal,
                    "cgst": cgst,
                    "sgst": sgst,
                    "total_amount": total_amount,
                    "item_count": len(line_items)
                }
            }
            
        except Exception as e:
            logging.error(f"Calculate total command failed: {e}")
            return {
                "success": False,
                "message": "I couldn't calculate the total right now.",
                "error": str(e)
            }
    
    def _handle_unknown_command(self, original_text: str, intent_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown or unclear commands"""
        return {
            "success": False,
            "message": "I'm not sure what you want me to do. Here are some things you can try:",
            "suggestions": [
                "Create invoice for [client name]",
                "Add [item] quantity [number] price [amount]",
                "Search client [name]",
                "Calculate total",
                "Show payment status for [invoice number]"
            ],
            "confidence": intent_analysis.get("confidence", 0.0)
        }
    
    def _log_voice_interaction(self, user_id: int, voice_text: str, 
                              intent_analysis: Dict[str, Any], result: Dict[str, Any]):
        """Log voice interaction for learning and improvement"""
        try:
            interaction = AIInteraction(
                user_id=user_id,
                interaction_type="voice_command",
                input_data={
                    "voice_text": voice_text,
                    "intent_analysis": intent_analysis
                },
                ai_response=result,
                confidence_score=intent_analysis.get("confidence", 0.0)
            )
            db.session.add(interaction)
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Failed to log voice interaction: {e}")

class VoiceInvoiceBuilder:
    """Specialized class for building invoices through voice commands"""
    
    def __init__(self):
        self.voice_processor = VoiceCommandProcessor()
    
    def start_voice_invoice_session(self, user_id: int, client_name: str = None) -> Dict[str, Any]:
        """Start a voice-guided invoice creation session"""
        session_data = {
            "user_id": user_id,
            "client_id": None,
            "client_name": client_name,
            "line_items": [],
            "session_state": "client_selection",
            "created_at": datetime.utcnow().isoformat()
        }
        
        if client_name:
            client = Client.query.filter(Client.name.ilike(f"%{client_name}%")).first()
            if client:
                session_data["client_id"] = client.id
                session_data["session_state"] = "adding_items"
                
                return {
                    "success": True,
                    "message": f"Starting invoice for {client.name}. Please tell me what items to add.",
                    "session_data": session_data,
                    "next_prompt": "Say 'Add [item description] quantity [number] price [amount]'"
                }
        
        return {
            "success": True,
            "message": "Let's create an invoice. Which client is this invoice for?",
            "session_data": session_data,
            "next_prompt": "Say 'Create invoice for [client name]'"
        }
    
    def process_session_command(self, session_data: Dict[str, Any], 
                               voice_command: str) -> Dict[str, Any]:
        """Process voice command within an active invoice session"""
        user_id = session_data.get("user_id")
        
        # Process the command with session context
        result = self.voice_processor.process_voice_command(
            user_id, voice_command, context=session_data
        )
        
        # Update session state based on result
        if result.get("success") and "invoice_context" in result:
            session_data.update(result["invoice_context"])
        
        return result

def initialize_voice_service():
    """Initialize voice services"""
    try:
        global voice_processor, voice_invoice_builder
        voice_processor = VoiceCommandProcessor()
        voice_invoice_builder = VoiceInvoiceBuilder()
        
        logging.info("Voice services initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize voice services: {e}")
        return False

# Global voice service instances
voice_processor = None
voice_invoice_builder = None
