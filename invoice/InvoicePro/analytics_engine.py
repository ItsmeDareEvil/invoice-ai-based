import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import func, desc, and_, or_
from collections import defaultdict
from sqlalchemy import func, desc
from models import Client, Invoice
from app import db
from models import Client
from app import db
from models import Invoice, Client, InvoiceLineItem, User, AIInteraction, ExpenseTracking, InventoryItem

class AnalyticsEngine:
    """Advanced analytics engine with AI-powered insights"""
    def fetch_top_clients(limit=10):
        query = (
            db.session.query(
                Client.id,
                Client.name,
                func.count(Invoice.id).label("invoice_count"),
                func.sum(Invoice.amount).label("total_revenue"),
                (func.sum(Invoice.amount) / func.count(Invoice.id)).label("avg_invoice_value")
            )
            .select_from(Invoice)
            .join(Client, Invoice.client_id == Client.id)
            .group_by(Client.id)
            .order_by(desc("total_revenue"))
            .limit(limit)
        )

        result = query.all()

        top_clients = []
        for r in result:
            top_clients.append({
                "name": r.name,
                "total_revenue": r.total_revenue,
                "invoice_count": r.invoice_count,
                "avg_invoice_value": r.avg_invoice_value
            })

        return top_clients
    def get_client_performance_metrics():
        """
        Returns client performance data for the analytics dashboard
        """
        client_performance = {
            'top_clients': fetch_top_clients(),
            'segments': {
                'by_value': {'high_value': 0, 'medium_value': 0, 'low_value': 0}
            },
            'lifecycle': {
                'stages': [
                    {'stage': 'In Discussion', 'count': 0},
                    {'stage': 'New', 'count': 0},
                    {'stage': 'Quoted', 'count': 0}
                ]
            },
            'risk_analysis': {
                'risk_distribution': {'high_risk': 0, 'medium_risk': 0, 'low_risk': 0}
            }
        }
        return client_performance

    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def get_revenue_trends(self, time_range: str = '12m') -> Dict[str, Any]:
        """Get revenue trends with predictive analysis"""
        try:
            # Parse time range
            months = self._parse_time_range(time_range)
            
            # Get historical revenue data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30 * months)
            
            monthly_revenue = db.session.query(
                func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
                func.sum(Invoice.total_amount).label('revenue'),
                func.count(Invoice.id).label('invoice_count'),
                func.avg(Invoice.total_amount).label('avg_invoice_value')
            ).filter(
                Invoice.invoice_date >= start_date.date(),
                Invoice.payment_status == 'Paid'
            ).group_by('month').order_by('month').all()
            
            # Calculate growth rates
            revenue_data = []
            previous_revenue = 0
            
            for i, data in enumerate(monthly_revenue):
                current_revenue = float(data.revenue or 0)
                growth_rate = 0
                
                if i > 0 and previous_revenue > 0:
                    growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
                
                revenue_data.append({
                    'month': data.month,
                    'revenue': current_revenue,
                    'invoice_count': data.invoice_count,
                    'avg_invoice_value': float(data.avg_invoice_value or 0),
                    'growth_rate': round(growth_rate, 2)
                })
                
                previous_revenue = current_revenue
            
            # Calculate trends and predictions
            total_revenue = sum(item['revenue'] for item in revenue_data)
            avg_monthly_revenue = total_revenue / len(revenue_data) if revenue_data else 0
            
            # Simple trend analysis
            recent_months = revenue_data[-3:] if len(revenue_data) >= 3 else revenue_data
            trend_direction = self._calculate_trend_direction(recent_months)
            
            return {
                'monthly_data': revenue_data,
                'summary': {
                    'total_revenue': total_revenue,
                    'avg_monthly_revenue': avg_monthly_revenue,
                    'trend_direction': trend_direction,
                    'total_invoices': sum(item['invoice_count'] for item in revenue_data),
                    'period_months': months
                }
            }
            
        except Exception as e:
            logging.error(f"Revenue trends analysis failed: {e}")
            return {'error': str(e)}
    
    def get_client_performance_metrics(self) -> Dict[str, Any]:
        """Comprehensive client performance analysis"""
        try:
            # Top performing clients
            top_clients = db.session.query(
                Client.id,
                Client.name,
                Client.client_type,
                Client.ai_risk_score,
                Client.predicted_ltv,
                func.sum(Invoice.total_amount).label('total_revenue'),
                func.count(Invoice.id).label('invoice_count'),
                func.avg(Invoice.total_amount).label('avg_invoice_value'),
                func.max(Invoice.invoice_date).label('last_invoice_date')
            ).join(Invoice).filter(
                Invoice.payment_status == 'Paid'
            ).group_by(Client.id).order_by(
                func.sum(Invoice.total_amount).desc()
            ).limit(20).all()
            
            # Client segmentation analysis
            client_segments = self._analyze_client_segments()
            
            # Client lifecycle analysis
            lifecycle_analysis = self._analyze_client_lifecycle()
            
            # Client risk analysis
            risk_analysis = self._analyze_client_risk()
            
            return {
                'top_clients': [
                    {
                        'id': client.id,
                        'name': client.name,
                        'type': client.client_type,
                        'total_revenue': float(client.total_revenue),
                        'invoice_count': client.invoice_count,
                        'avg_invoice_value': float(client.avg_invoice_value),
                        'last_invoice_date': client.last_invoice_date.isoformat() if client.last_invoice_date else None,
                        'risk_score': float(client.ai_risk_score or 0),
                        'predicted_ltv': float(client.predicted_ltv or 0)
                    }
                    for client in top_clients
                ],
                'segments': client_segments,
                'lifecycle': lifecycle_analysis,
                'risk_analysis': risk_analysis
            }
            
        except Exception as e:
            logging.error(f"Client performance analysis failed: {e}")
            return {'error': str(e)}
    
    def get_payment_analytics(self) -> Dict[str, Any]:
        """Advanced payment behavior analytics"""
        try:
            # Payment status distribution
            payment_status_dist = db.session.query(
                Invoice.payment_status,
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.total_amount).label('amount')
            ).group_by(Invoice.payment_status).all()
            
            # Payment timing analysis
            payment_timing = db.session.query(
                func.avg(
                    func.julianday(Invoice.payment_date) - func.julianday(Invoice.due_date)
                ).label('avg_delay'),
                func.min(
                    func.julianday(Invoice.payment_date) - func.julianday(Invoice.due_date)
                ).label('min_delay'),
                func.max(
                    func.julianday(Invoice.payment_date) - func.julianday(Invoice.due_date)
                ).label('max_delay')
            ).filter(
                Invoice.payment_status == 'Paid',
                Invoice.payment_date.isnot(None),
                Invoice.due_date.isnot(None)
            ).first()
            
            # Payment mode analysis
            payment_modes = db.session.query(
                Invoice.payment_mode,
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.total_amount).label('amount')
            ).filter(
                Invoice.payment_status == 'Paid',
                Invoice.payment_mode.isnot(None)
            ).group_by(Invoice.payment_mode).all()
            
            # Monthly collection trends
            monthly_collections = db.session.query(
                func.strftime('%Y-%m', Invoice.payment_date).label('month'),
                func.sum(Invoice.total_amount).label('collected'),
                func.count(Invoice.id).label('invoices_paid')
            ).filter(
                Invoice.payment_status == 'Paid',
                Invoice.payment_date >= (datetime.now() - timedelta(days=365)).date()
            ).group_by('month').order_by('month').all()
            
            # Outstanding analysis
            outstanding_analysis = self._analyze_outstanding_invoices()
            
            return {
                'payment_status_distribution': [
                    {
                        'status': item.payment_status,
                        'count': item.count,
                        'amount': float(item.amount or 0)
                    }
                    for item in payment_status_dist
                ],
                'payment_timing': {
                    'avg_delay_days': float(payment_timing.avg_delay or 0),
                    'min_delay_days': float(payment_timing.min_delay or 0),
                    'max_delay_days': float(payment_timing.max_delay or 0)
                },
                'payment_modes': [
                    {
                        'mode': item.payment_mode,
                        'count': item.count,
                        'amount': float(item.amount)
                    }
                    for item in payment_modes
                ],
                'monthly_collections': [
                    {
                        'month': item.month,
                        'collected': float(item.collected),
                        'invoices_paid': item.invoices_paid
                    }
                    for item in monthly_collections
                ],
                'outstanding': outstanding_analysis
            }
            
        except Exception as e:
            logging.error(f"Payment analytics failed: {e}")
            return {'error': str(e)}
    
    def get_profitability_analysis(self) -> Dict[str, Any]:
        """Detailed profitability analysis with cost tracking"""
        try:
            # Overall profitability
            overall_profit = db.session.query(
                func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).label('total_revenue'),
                func.sum(InvoiceLineItem.cost_price * InvoiceLineItem.quantity).label('total_cost')
            ).join(Invoice).filter(
                Invoice.payment_status == 'Paid'
            ).first()
            
            total_revenue = float(overall_profit.total_revenue or 0)
            total_cost = float(overall_profit.total_cost or 0)
            total_profit = total_revenue - total_cost
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Monthly profitability trends
            monthly_profit = db.session.query(
                func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
                func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).label('revenue'),
                func.sum(InvoiceLineItem.cost_price * InvoiceLineItem.quantity).label('cost')
            ).join(Invoice).filter(
                Invoice.payment_status == 'Paid',
                Invoice.invoice_date >= (datetime.now() - timedelta(days=365)).date()
            ).group_by('month').order_by('month').all()
            
            monthly_data = []
            for item in monthly_profit:
                revenue = float(item.revenue or 0)
                cost = float(item.cost or 0)
                profit = revenue - cost
                margin = (profit / revenue * 100) if revenue > 0 else 0
                
                monthly_data.append({
                    'month': item.month,
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percentage': round(margin, 2)
                })
            
            # Client profitability analysis
            client_profitability = db.session.query(
                Client.id,
                Client.name,
                func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).label('revenue'),
                func.sum(InvoiceLineItem.cost_price * InvoiceLineItem.quantity).label('cost')
            ).join(Invoice).join(InvoiceLineItem).filter(
                Invoice.payment_status == 'Paid'
            ).group_by(Client.id).order_by(
                func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).desc()
            ).limit(10).all()
            
            client_data = []
            for client in client_profitability:
                revenue = float(client.revenue or 0)
                cost = float(client.cost or 0)
                profit = revenue - cost
                margin = (profit / revenue * 100) if revenue > 0 else 0
                
                client_data.append({
                    'id': client.id,
                    'name': client.name,
                    'revenue': revenue,
                    'cost': cost,
                    'profit': profit,
                    'margin_percentage': round(margin, 2)
                })
            
            return {
                'overall': {
                    'total_revenue': total_revenue,
                    'total_cost': total_cost,
                    'total_profit': total_profit,
                    'profit_margin_percentage': round(profit_margin, 2)
                },
                'monthly_trends': monthly_data,
                'top_profitable_clients': client_data
            }
            
        except Exception as e:
            logging.error(f"Profitability analysis failed: {e}")
            return {'error': str(e)}
    
    def get_ai_insights(self) -> Dict[str, Any]:
        """AI-powered business insights and recommendations"""
        try:
            # AI interaction analytics
            ai_interactions = db.session.query(
                AIInteraction.interaction_type,
                func.count(AIInteraction.id).label('count'),
                func.avg(AIInteraction.confidence_score).label('avg_confidence'),
                func.avg(AIInteraction.processing_time).label('avg_processing_time')
            ).group_by(AIInteraction.interaction_type).all()
            
            # Voice command usage
            voice_usage = db.session.query(
                func.count(Invoice.id).label('voice_created_count')
            ).filter(Invoice.voice_command_created == True).scalar()
            
            total_invoices = db.session.query(func.count(Invoice.id)).scalar()
            voice_adoption_rate = (voice_usage / total_invoices * 100) if total_invoices > 0 else 0
            
            # AI suggestion acceptance rate
            ai_suggestions_applied = db.session.query(
                func.count(InvoiceLineItem.id)
            ).filter(InvoiceLineItem.ai_suggested == True).scalar()
            
            total_line_items = db.session.query(func.count(InvoiceLineItem.id)).scalar()
            ai_suggestion_rate = (ai_suggestions_applied / total_line_items * 100) if total_line_items > 0 else 0
            
            # Generate business recommendations
            recommendations = self._generate_business_recommendations()
            
            return {
                'ai_interactions': [
                    {
                        'type': item.interaction_type,
                        'count': item.count,
                        'avg_confidence': float(item.avg_confidence or 0),
                        'avg_processing_time': float(item.avg_processing_time or 0)
                    }
                    for item in ai_interactions
                ],
                'voice_adoption': {
                    'voice_created_invoices': voice_usage or 0,
                    'total_invoices': total_invoices or 0,
                    'adoption_rate_percentage': round(voice_adoption_rate, 2)
                },
                'ai_suggestions': {
                    'suggestions_applied': ai_suggestions_applied or 0,
                    'total_line_items': total_line_items or 0,
                    'acceptance_rate_percentage': round(ai_suggestion_rate, 2)
                },
                'recommendations': recommendations
            }
            
        except Exception as e:
            logging.error(f"AI insights analysis failed: {e}")
            return {'error': str(e)}
    
    def get_monthly_revenue_trend(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly revenue trend data for charts"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30 * months)
            
            monthly_data = db.session.query(
                func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
                func.sum(Invoice.total_amount).label('revenue')
            ).filter(
                Invoice.invoice_date >= start_date.date(),
                Invoice.payment_status == 'Paid'
            ).group_by('month').order_by('month').all()
            
            # Fill in missing months with zero revenue
            revenue_dict = {item.month: float(item.revenue) for item in monthly_data}
            
            result = []
            current_date = start_date.replace(day=1)
            while current_date <= end_date:
                month_key = current_date.strftime('%Y-%m')
                month_label = current_date.strftime('%b %Y')
                revenue = revenue_dict.get(month_key, 0)
                
                result.append({
                    'month': month_label,
                    'revenue': revenue
                })
                
                # Move to next month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            
            return result
            
        except Exception as e:
            logging.error(f"Monthly revenue trend failed: {e}")
            return []
    
    def get_ai_invoice_insights(self, invoice_ids: List[int]) -> Dict[str, Any]:
        """Get AI insights for specific invoices"""
        try:
            insights = {}
            
            for invoice_id in invoice_ids:
                invoice = Invoice.query.get(invoice_id)
                if not invoice:
                    continue
                
                invoice_insights = {
                    'payment_risk': 'Low',
                    'predicted_payment_date': None,
                    'ai_confidence': 0.0
                }
                
                # Risk assessment based on client history
                if invoice.client.ai_risk_score:
                    if invoice.client.ai_risk_score > 0.7:
                        invoice_insights['payment_risk'] = 'High'
                    elif invoice.client.ai_risk_score > 0.4:
                        invoice_insights['payment_risk'] = 'Medium'
                    else:
                        invoice_insights['payment_risk'] = 'Low'
                
                # Predicted payment date
                if invoice.predicted_payment_date:
                    invoice_insights['predicted_payment_date'] = invoice.predicted_payment_date.isoformat()
                
                # AI risk assessment confidence
                if invoice.ai_risk_assessment:
                    invoice_insights['ai_confidence'] = invoice.ai_risk_assessment.get('confidence', 0.0)
                
                insights[invoice_id] = invoice_insights
            
            return insights
            
        except Exception as e:
            logging.error(f"AI invoice insights failed: {e}")
            return {}
    
    def find_similar_invoices(self, invoice_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar invoices based on AI analysis"""
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice:
                return []
            
            # Find invoices with similar amounts and same client
            similar_invoices = Invoice.query.filter(
                Invoice.id != invoice_id,
                Invoice.client_id == invoice.client_id,
                Invoice.total_amount.between(
                    invoice.total_amount * 0.8,
                    invoice.total_amount * 1.2
                )
            ).order_by(Invoice.invoice_date.desc()).limit(limit).all()
            
            result = []
            for similar_invoice in similar_invoices:
                result.append({
                    'id': similar_invoice.id,
                    'invoice_number': similar_invoice.invoice_number,
                    'date': similar_invoice.invoice_date.isoformat(),
                    'amount': float(similar_invoice.total_amount),
                    'payment_status': similar_invoice.payment_status,
                    'similarity_score': self._calculate_similarity_score(invoice, similar_invoice)
                })
            
            return result
            
        except Exception as e:
            logging.error(f"Similar invoices search failed: {e}")
            return []
    
    # Helper methods
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to months"""
        if time_range.endswith('m'):
            return int(time_range[:-1])
        elif time_range.endswith('y'):
            return int(time_range[:-1]) * 12
        else:
            return 12  # Default to 12 months
    
    def _calculate_trend_direction(self, recent_data: List[Dict]) -> str:
        """Calculate trend direction from recent data"""
        if len(recent_data) < 2:
            return 'stable'
        
        revenues = [item['revenue'] for item in recent_data]
        
        # Simple trend calculation
        if revenues[-1] > revenues[0]:
            return 'increasing'
        elif revenues[-1] < revenues[0]:
            return 'decreasing'
        else:
            return 'stable'
    
    def _analyze_client_segments(self) -> Dict[str, Any]:
        """Analyze client segments"""
        try:
            # Segment by revenue
            high_value = db.session.query(func.count(Client.id)).join(Invoice).filter(
                Invoice.payment_status == 'Paid'
            ).group_by(Client.id).having(
                func.sum(Invoice.total_amount) > 100000
            ).count()
            
            medium_value = db.session.query(func.count(Client.id)).join(Invoice).filter(
                Invoice.payment_status == 'Paid'
            ).group_by(Client.id).having(
                and_(
                    func.sum(Invoice.total_amount) >= 25000,
                    func.sum(Invoice.total_amount) <= 100000
                )
            ).count()
            
            low_value = db.session.query(func.count(Client.id)).join(Invoice).filter(
                Invoice.payment_status == 'Paid'
            ).group_by(Client.id).having(
                func.sum(Invoice.total_amount) < 25000
            ).count()
            
            return {
                'by_value': {
                    'high_value': high_value,
                    'medium_value': medium_value,
                    'low_value': low_value
                }
            }
            
        except Exception as e:
            logging.error(f"Client segmentation failed: {e}")
            return {}
    
    def _analyze_client_lifecycle(self) -> Dict[str, Any]:
        """Analyze client lifecycle stages"""
        try:
            lifecycle_data = db.session.query(
                Client.lead_stage,
                func.count(Client.id).label('count')
            ).group_by(Client.lead_stage).all()
            
            return {
                'stages': [
                    {'stage': item.lead_stage, 'count': item.count}
                    for item in lifecycle_data
                ]
            }
            
        except Exception as e:
            logging.error(f"Client lifecycle analysis failed: {e}")
            return {}
    
    def _analyze_client_risk(self) -> Dict[str, Any]:
        """Analyze client risk distribution"""
        try:
            high_risk = db.session.query(func.count(Client.id)).filter(
                Client.ai_risk_score > 0.7
            ).scalar() or 0
            
            medium_risk = db.session.query(func.count(Client.id)).filter(
                and_(Client.ai_risk_score >= 0.3, Client.ai_risk_score <= 0.7)
            ).scalar() or 0
            
            low_risk = db.session.query(func.count(Client.id)).filter(
                Client.ai_risk_score < 0.3
            ).scalar() or 0
            
            return {
                'risk_distribution': {
                    'high_risk': high_risk,
                    'medium_risk': medium_risk,
                    'low_risk': low_risk
                }
            }
            
        except Exception as e:
            logging.error(f"Client risk analysis failed: {e}")
            return {}
    
    def _analyze_outstanding_invoices(self) -> Dict[str, Any]:
        """Analyze outstanding invoices"""
        try:
            current_date = datetime.now().date()
            
            # Outstanding by age
            overdue_30 = db.session.query(
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.total_amount - Invoice.amount_paid).label('amount')
            ).filter(
                Invoice.payment_status.in_(['Unpaid', 'Partially Paid']),
                Invoice.due_date < current_date - timedelta(days=30)
            ).first()
            
            overdue_60 = db.session.query(
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.total_amount - Invoice.amount_paid).label('amount')
            ).filter(
                Invoice.payment_status.in_(['Unpaid', 'Partially Paid']),
                Invoice.due_date < current_date - timedelta(days=60)
            ).first()
            
            overdue_90 = db.session.query(
                func.count(Invoice.id).label('count'),
                func.sum(Invoice.total_amount - Invoice.amount_paid).label('amount')
            ).filter(
                Invoice.payment_status.in_(['Unpaid', 'Partially Paid']),
                Invoice.due_date < current_date - timedelta(days=90)
            ).first()
            
            return {
                'aging_analysis': {
                    '30_days': {
                        'count': overdue_30.count or 0,
                        'amount': float(overdue_30.amount or 0)
                    },
                    '60_days': {
                        'count': overdue_60.count or 0,
                        'amount': float(overdue_60.amount or 0)
                    },
                    '90_days': {
                        'count': overdue_90.count or 0,
                        'amount': float(overdue_90.amount or 0)
                    }
                }
            }
            
        except Exception as e:
            logging.error(f"Outstanding analysis failed: {e}")
            return {}
    
    def _generate_business_recommendations(self) -> List[str]:
        """Generate AI-powered business recommendations"""
        try:
            recommendations = []
            
            # Analyze recent trends and generate recommendations
            recent_revenue = self.get_revenue_trends('3m')
            if 'summary' in recent_revenue:
                trend = recent_revenue['summary'].get('trend_direction', 'stable')
                
                if trend == 'decreasing':
                    recommendations.append("Revenue is declining. Consider reaching out to high-value clients for new projects.")
                    recommendations.append("Review pricing strategy and consider offering promotional packages.")
                elif trend == 'increasing':
                    recommendations.append("Revenue growth is positive. Consider expanding service offerings.")
                    recommendations.append("Focus on client retention strategies to maintain growth momentum.")
            
            # Payment behavior recommendations
            payment_analytics = self.get_payment_analytics()
            if 'payment_timing' in payment_analytics:
                avg_delay = payment_analytics['payment_timing'].get('avg_delay_days', 0)
                
                if avg_delay > 15:
                    recommendations.append("Average payment delay is high. Implement automated payment reminders.")
                    recommendations.append("Consider offering early payment discounts to improve cash flow.")
            
            # Client risk recommendations
            high_risk_clients = db.session.query(func.count(Client.id)).filter(
                Client.ai_risk_score > 0.7
            ).scalar() or 0
            
            if high_risk_clients > 0:
                recommendations.append(f"You have {high_risk_clients} high-risk clients. Review credit terms and payment history.")
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logging.error(f"Business recommendations generation failed: {e}")
            return ["Unable to generate recommendations at this time."]
    
    def _calculate_similarity_score(self, invoice1: Invoice, invoice2: Invoice) -> float:
        """Calculate similarity score between two invoices"""
        try:
            score = 0.0
            
            # Amount similarity (40% weight)
            amount_diff = abs(invoice1.total_amount - invoice2.total_amount)
            max_amount = max(invoice1.total_amount, invoice2.total_amount)
            amount_similarity = 1 - (amount_diff / max_amount) if max_amount > 0 else 1
            score += amount_similarity * 0.4
            
            # Client similarity (30% weight)
            if invoice1.client_id == invoice2.client_id:
                score += 0.3
            
            # Date proximity (20% weight)
            date_diff = abs((invoice1.invoice_date - invoice2.invoice_date).days)
            date_similarity = max(0, 1 - (date_diff / 365))  # Similarity decreases over a year
            score += date_similarity * 0.2
            
            # Item count similarity (10% weight)
            count1 = len(invoice1.line_items)
            count2 = len(invoice2.line_items)
            count_diff = abs(count1 - count2)
            max_count = max(count1, count2)
            count_similarity = 1 - (count_diff / max_count) if max_count > 0 else 1
            score += count_similarity * 0.1
            
            return round(score, 2)
            
        except Exception as e:
            logging.error(f"Similarity calculation failed: {e}")
            return 0.0

    def __init__(self, db_session):
        self.db_session = db_session

    # Existing methods ...

    def get_lead_stats(self):
        
 
        results = (
            self.db_session.query(Client.lead_stage, func.count(Client.id))
            .group_by(Client.lead_stage)
            .all()
        )

        stats = {"new": 0, "discussion": 0, "quoted": 0, "closed": 0}

        for stage, count in results:
            stage_lower = stage.lower() if stage else "new"
            if "new" in stage_lower:
                stats["new"] = count
            elif "discussion" in stage_lower:
                stats["discussion"] = count
            elif "quote" in stage_lower:
                stats["quoted"] = count
            elif "closed" in stage_lower:
                stats["closed"] = count

        return stats
