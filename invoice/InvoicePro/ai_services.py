import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import openai
from sqlalchemy import func
from app import db
from models import Invoice, Client, InvoiceLineItem, AIInteraction, InventoryItem

# Initialize OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY")

class AIInvoiceAssistant:
    """AI-powered invoice assistance with GPT-4o"""
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        
    def analyze_client_history(self, client_id: int) -> Dict[str, Any]:
        """Analyze client's invoice history to provide insights"""
        try:
            client = Client.query.get(client_id)
            if not client:
                return {"error": "Client not found"}
            
            # Get client's invoice history
            invoices = Invoice.query.filter_by(client_id=client_id).all()
            
            # Prepare data for AI analysis
            invoice_data = []
            for invoice in invoices:
                invoice_info = {
                    "date": invoice.invoice_date.strftime("%Y-%m-%d"),
                    "amount": float(invoice.total_amount),
                    "payment_status": invoice.payment_status,
                    "items": [{"description": item.description, "quantity": item.quantity, "price": item.unit_price} 
                             for item in invoice.line_items]
                }
                invoice_data.append(invoice_info)
            
            # AI analysis prompt
            prompt = f"""
            Analyze the following client invoice history and provide insights in JSON format:
            
            Client: {client.name}
            Invoice History: {json.dumps(invoice_data, indent=2)}
            
            Provide analysis in this JSON format:
            {{
                "payment_behavior": "description of payment patterns",
                "average_order_value": float,
                "preferred_products": ["list of frequently ordered items"],
                "seasonal_patterns": "description of seasonal trends",
                "risk_assessment": {{
                    "score": float between 0-1,
                    "factors": ["list of risk factors"]
                }},
                "recommendations": ["list of business recommendations"],
                "predicted_ltv": float,
                "next_order_prediction": {{
                    "likely_date": "YYYY-MM-DD",
                    "estimated_value": float,
                    "suggested_products": ["list"]
                }}
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Update client with AI insights
            client.ai_risk_score = analysis.get("risk_assessment", {}).get("score", 0.0)
            client.predicted_ltv = analysis.get("predicted_ltv", 0.0)
            client.preferred_products = analysis.get("preferred_products", [])
            
            db.session.commit()
            
            return analysis
            
        except Exception as e:
            logging.error(f"AI client analysis failed: {e}")
            return {"error": str(e)}
    
    def suggest_invoice_items(self, client_id: int, context: str = "") -> List[Dict[str, Any]]:
        """AI-powered item suggestions based on client history and context"""
        try:
            client = Client.query.get(client_id)
            if not client:
                return []
            
            # Get recent invoices for this client
            recent_invoices = Invoice.query.filter_by(client_id=client_id)\
                .order_by(Invoice.invoice_date.desc())\
                .limit(10).all()
            
            # Get inventory items
            inventory_items = InventoryItem.query.all()
            
            # Prepare context for AI
            client_history = []
            for invoice in recent_invoices:
                for item in invoice.line_items:
                    client_history.append({
                        "description": item.description,
                        "quantity": item.quantity,
                        "price": item.unit_price,
                        "date": invoice.invoice_date.strftime("%Y-%m-%d")
                    })
            
            inventory_context = [{"name": item.name, "description": item.description, 
                                "price": item.selling_price, "stock": item.current_stock}
                               for item in inventory_items if item.current_stock > 0]
            
            prompt = f"""
            Based on the client history and available inventory, suggest relevant invoice items:
            
            Client: {client.name}
            Context: {context}
            Client Purchase History: {json.dumps(client_history[-20:], indent=2)}
            Available Inventory: {json.dumps(inventory_context[:50], indent=2)}
            
            Suggest 5-10 relevant items in JSON format:
            {{
                "suggestions": [
                    {{
                        "description": "item description",
                        "quantity": float,
                        "unit_price": float,
                        "reasoning": "why this item is suggested",
                        "confidence": float between 0-1
                    }}
                ]
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            suggestions = json.loads(response.choices[0].message.content)
            return suggestions.get("suggestions", [])
            
        except Exception as e:
            logging.error(f"AI item suggestions failed: {e}")
            return []
    
    def optimize_pricing(self, items: List[Dict], client_id: int) -> List[Dict]:
        """AI-powered pricing optimization"""
        try:
            client = Client.query.get(client_id)
            market_data = self._get_market_pricing_data()
            
            prompt = f"""
            Optimize pricing for the following items based on client profile and market data:
            
            Client Profile: Risk Score: {client.ai_risk_score}, LTV: {client.predicted_ltv}
            Items: {json.dumps(items, indent=2)}
            Market Data: {json.dumps(market_data, indent=2)}
            
            Provide optimized pricing in JSON format:
            {{
                "optimized_items": [
                    {{
                        "original_price": float,
                        "optimized_price": float,
                        "reasoning": "explanation for price change",
                        "confidence": float
                    }}
                ]
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            optimization = json.loads(response.choices[0].message.content)
            return optimization.get("optimized_items", [])
            
        except Exception as e:
            logging.error(f"AI pricing optimization failed: {e}")
            return items
    
    def _get_market_pricing_data(self) -> Dict:
        """Get market pricing context from recent invoices"""
        recent_items = db.session.query(InvoiceLineItem.description, 
                                      func.avg(InvoiceLineItem.unit_price).label('avg_price'))\
            .join(Invoice)\
            .filter(Invoice.invoice_date >= datetime.now() - timedelta(days=90))\
            .group_by(InvoiceLineItem.description)\
            .limit(100).all()
        
        return {item.description: float(item.avg_price) for item in recent_items}

class PredictiveAnalytics:
    """Advanced predictive analytics for business insights"""
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
    
    def predict_cash_flow(self, months_ahead: int = 6) -> Dict[str, Any]:
        """Predict cash flow for upcoming months"""
        try:
            # Get historical data
            current_date = datetime.now()
            historical_data = []
            
            for i in range(12):  # Last 12 months
                month_start = current_date.replace(day=1) - timedelta(days=30*i)
                month_end = month_start + timedelta(days=30)
                
                revenue = db.session.query(func.sum(Invoice.total_amount))\
                    .filter(Invoice.invoice_date.between(month_start.date(), month_end.date()))\
                    .filter(Invoice.payment_status == 'Paid').scalar() or 0
                
                outstanding = db.session.query(func.sum(Invoice.total_amount))\
                    .filter(Invoice.invoice_date.between(month_start.date(), month_end.date()))\
                    .filter(Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])).scalar() or 0
                
                historical_data.append({
                    "month": month_start.strftime("%Y-%m"),
                    "revenue": float(revenue),
                    "outstanding": float(outstanding)
                })
            
            # Get upcoming invoices
            upcoming_invoices = Invoice.query.filter(
                Invoice.due_date >= current_date.date(),
                Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
            ).all()
            
            upcoming_data = [{"due_date": inv.due_date.strftime("%Y-%m-%d"), 
                            "amount": float(inv.total_amount)} for inv in upcoming_invoices]
            
            prompt = f"""
            Predict cash flow for the next {months_ahead} months based on historical data and upcoming payments:
            
            Historical Data (last 12 months): {json.dumps(historical_data, indent=2)}
            Upcoming Invoices: {json.dumps(upcoming_data, indent=2)}
            
            Provide predictions in JSON format:
            {{
                "monthly_predictions": [
                    {{
                        "month": "YYYY-MM",
                        "predicted_revenue": float,
                        "predicted_collections": float,
                        "confidence_level": float,
                        "key_factors": ["list of factors affecting prediction"]
                    }}
                ],
                "summary": {{
                    "total_predicted_revenue": float,
                    "cash_flow_trend": "improving/stable/declining",
                    "risk_factors": ["list of risks"],
                    "recommendations": ["list of recommendations"]
                }}
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            prediction = json.loads(response.choices[0].message.content)
            return prediction
            
        except Exception as e:
            logging.error(f"Cash flow prediction failed: {e}")
            return {"error": str(e)}
    
    def analyze_client_payment_patterns(self) -> Dict[str, Any]:
        """Analyze payment patterns across all clients"""
        try:
            # Get payment data
            payment_data = db.session.query(
                Client.name,
                Client.id,
                func.avg(func.julianday(Invoice.payment_date) - func.julianday(Invoice.due_date)).label('avg_delay'),
                func.count(Invoice.id).label('invoice_count'),
                func.sum(Invoice.total_amount).label('total_business')
            ).join(Invoice)\
            .filter(Invoice.payment_status == 'Paid')\
            .filter(Invoice.payment_date.isnot(None))\
            .group_by(Client.id).all()
            
            analysis_data = []
            for data in payment_data:
                analysis_data.append({
                    "client_name": data.name,
                    "avg_payment_delay_days": float(data.avg_delay or 0),
                    "invoice_count": data.invoice_count,
                    "total_business": float(data.total_business)
                })
            
            prompt = f"""
            Analyze client payment patterns and provide insights:
            
            Payment Data: {json.dumps(analysis_data, indent=2)}
            
            Provide analysis in JSON format:
            {{
                "payment_behavior_segments": [
                    {{
                        "segment_name": "Early Payers/On-time/Late Payers",
                        "characteristics": "description",
                        "client_count": int,
                        "avg_delay_days": float,
                        "business_impact": "positive/neutral/negative"
                    }}
                ],
                "insights": {{
                    "best_performing_clients": ["list of client names"],
                    "at_risk_clients": ["list of client names"],
                    "overall_collection_health": "excellent/good/fair/poor",
                    "recommendations": ["list of recommendations"]
                }},
                "predictions": {{
                    "clients_likely_to_default": ["list with reasons"],
                    "improvement_opportunities": ["list of opportunities"]
                }}
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logging.error(f"Payment pattern analysis failed: {e}")
            return {"error": str(e)}

class InventoryAI:
    """AI-powered inventory management and demand forecasting"""
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
    
    def forecast_demand(self, item_id: int, days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast demand for inventory items"""
        try:
            item = InventoryItem.query.get(item_id)
            if not item:
                return {"error": "Item not found"}
            
            # Get historical sales data
            sales_data = db.session.query(
                InvoiceLineItem.quantity,
                Invoice.invoice_date
            ).join(Invoice)\
            .filter(InvoiceLineItem.description.contains(item.name))\
            .filter(Invoice.payment_status == 'Paid')\
            .order_by(Invoice.invoice_date.desc())\
            .limit(100).all()
            
            historical_sales = [{"date": sale.invoice_date.strftime("%Y-%m-%d"), 
                               "quantity": float(sale.quantity)} for sale in sales_data]
            
            prompt = f"""
            Forecast demand for inventory item based on historical sales:
            
            Item: {item.name}
            Current Stock: {item.current_stock}
            Historical Sales: {json.dumps(historical_sales, indent=2)}
            Forecast Period: {days_ahead} days
            
            Provide forecast in JSON format:
            {{
                "demand_forecast": {{
                    "total_demand": float,
                    "daily_average": float,
                    "peak_demand_days": ["list of likely peak days"],
                    "confidence_level": float
                }},
                "reorder_recommendation": {{
                    "should_reorder": boolean,
                    "suggested_quantity": float,
                    "reorder_urgency": "low/medium/high",
                    "reasoning": "explanation"
                }},
                "seasonal_insights": {{
                    "pattern_detected": boolean,
                    "seasonal_factors": ["list of factors"],
                    "next_peak_period": "description"
                }}
            }}
            """
            
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            forecast = json.loads(response.choices[0].message.content)
            
            # Update item with AI insights
            item.ai_demand_forecast = forecast
            item.ai_reorder_suggestions = forecast.get("reorder_recommendation", {})
            db.session.commit()
            
            return forecast
            
        except Exception as e:
            logging.error(f"Demand forecasting failed: {e}")
            return {"error": str(e)}

def initialize_ai_models():
    """Initialize AI services and perform health checks"""
    try:
        # Test OpenAI connection
        if not openai.api_key:
            raise Exception("OpenAI API key not configured")
        
        # Initialize AI services
        global ai_assistant, predictive_analytics, inventory_ai
        ai_assistant = AIInvoiceAssistant()
        predictive_analytics = PredictiveAnalytics()
        inventory_ai = InventoryAI()
        
        logging.info("AI services initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize AI services: {e}")
        return False

# Global AI service instances
ai_assistant = None
predictive_analytics = None
inventory_ai = None
