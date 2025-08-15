import hashlib
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os
from app import db
from models import BlockchainRecord, SmartContract, Invoice

class BlockchainInvoiceVerification:
    """Blockchain-based invoice verification system"""
    
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.blockchain_file = os.path.join(os.getcwd(), "blockchain_data", "invoice_chain.json")
        self.load_blockchain()
    
    def create_genesis_block(self) -> Dict[str, Any]:
        """Create the first block in the blockchain"""
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": [],
            "previous_hash": "0",
            "nonce": 0
        }
        genesis_block["hash"] = self.calculate_hash(genesis_block)
        return genesis_block
    
    def calculate_hash(self, block: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of a block"""
        block_string = json.dumps(block, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def create_invoice_transaction(self, invoice_id: int, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a blockchain transaction for invoice verification"""
        transaction = {
            "type": "invoice_creation",
            "invoice_id": invoice_id,
            "timestamp": time.time(),
            "data": {
                "invoice_number": invoice_data.get("invoice_number"),
                "client_id": invoice_data.get("client_id"),
                "total_amount": invoice_data.get("total_amount"),
                "invoice_date": invoice_data.get("invoice_date"),
                "line_items_hash": self.hash_line_items(invoice_data.get("line_items", []))
            },
            "hash": ""
        }
        
        # Calculate transaction hash
        transaction_string = json.dumps(transaction, sort_keys=True)
        transaction["hash"] = hashlib.sha256(transaction_string.encode()).hexdigest()
        
        return transaction
    
    def hash_line_items(self, line_items: list) -> str:
        """Create a hash of invoice line items for integrity verification"""
        items_data = []
        for item in line_items:
            item_data = {
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("unit_price", 0),
                "total_amount": item.get("total_amount", 0)
            }
            items_data.append(item_data)
        
        items_string = json.dumps(items_data, sort_keys=True)
        return hashlib.sha256(items_string.encode()).hexdigest()
    
    def add_invoice_to_blockchain(self, invoice: Invoice) -> str:
        """Add invoice to blockchain for verification"""
        try:
            # Prepare invoice data
            invoice_data = {
                "invoice_number": invoice.invoice_number,
                "client_id": invoice.client_id,
                "total_amount": float(invoice.total_amount),
                "invoice_date": invoice.invoice_date.isoformat(),
                "line_items": [
                    {
                        "description": item.description,
                        "quantity": float(item.quantity),
                        "unit_price": float(item.unit_price),
                        "total_amount": float(item.total_amount)
                    }
                    for item in invoice.line_items
                ]
            }
            
            # Create transaction
            transaction = self.create_invoice_transaction(invoice.id, invoice_data)
            self.pending_transactions.append(transaction)
            
            # Mine block with pending transactions
            new_block = self.mine_block()
            
            # Save blockchain record to database
            blockchain_record = BlockchainRecord(
                record_type="invoice",
                record_id=invoice.id,
                blockchain_hash=transaction["hash"],
                block_number=new_block["index"],
                transaction_hash=transaction["hash"],
                verification_status="verified"
            )
            db.session.add(blockchain_record)
            
            # Update invoice with blockchain hash
            invoice.blockchain_hash = transaction["hash"]
            invoice.blockchain_timestamp = datetime.utcnow()
            
            db.session.commit()
            
            # Save blockchain to file
            self.save_blockchain()
            
            logging.info(f"Invoice {invoice.invoice_number} added to blockchain with hash {transaction['hash']}")
            return transaction["hash"]
            
        except Exception as e:
            logging.error(f"Failed to add invoice to blockchain: {e}")
            return ""
    
    def mine_block(self, difficulty: int = 4) -> Dict[str, Any]:
        """Mine a new block with pending transactions"""
        if not self.pending_transactions:
            return None
        
        # Get the last block
        last_block = self.chain[-1] if self.chain else self.create_genesis_block()
        
        # Create new block
        new_block = {
            "index": last_block["index"] + 1,
            "timestamp": time.time(),
            "transactions": self.pending_transactions.copy(),
            "previous_hash": last_block["hash"],
            "nonce": 0
        }
        
        # Proof of Work
        target = "0" * difficulty
        while not self.calculate_hash(new_block).startswith(target):
            new_block["nonce"] += 1
        
        new_block["hash"] = self.calculate_hash(new_block)
        
        # Add block to chain
        self.chain.append(new_block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        return new_block
    
    def verify_invoice_integrity(self, invoice_id: int) -> Dict[str, Any]:
        """Verify invoice integrity using blockchain"""
        try:
            invoice = Invoice.query.get(invoice_id)
            if not invoice or not invoice.blockchain_hash:
                return {"verified": False, "reason": "Invoice not found or not on blockchain"}
            
            # Find transaction in blockchain
            transaction = None
            for block in self.chain:
                for tx in block["transactions"]:
                    if tx.get("invoice_id") == invoice_id:
                        transaction = tx
                        break
                if transaction:
                    break
            
            if not transaction:
                return {"verified": False, "reason": "Transaction not found in blockchain"}
            
            # Verify current invoice data against blockchain
            current_data = {
                "invoice_number": invoice.invoice_number,
                "client_id": invoice.client_id,
                "total_amount": float(invoice.total_amount),
                "invoice_date": invoice.invoice_date.isoformat(),
                "line_items": [
                    {
                        "description": item.description,
                        "quantity": float(item.quantity),
                        "unit_price": float(item.unit_price),
                        "total_amount": float(item.total_amount)
                    }
                    for item in invoice.line_items
                ]
            }
            
            # Compare with blockchain data
            blockchain_data = transaction["data"]
            current_hash = self.hash_line_items(current_data["line_items"])
            
            verification_result = {
                "verified": True,
                "blockchain_hash": transaction["hash"],
                "timestamp": transaction["timestamp"],
                "block_index": None,
                "integrity_check": current_hash == blockchain_data["line_items_hash"]
            }
            
            # Find block index
            for block in self.chain:
                if transaction in block["transactions"]:
                    verification_result["block_index"] = block["index"]
                    break
            
            if not verification_result["integrity_check"]:
                verification_result["verified"] = False
                verification_result["reason"] = "Invoice data has been modified since blockchain entry"
            
            return verification_result
            
        except Exception as e:
            logging.error(f"Invoice verification failed: {e}")
            return {"verified": False, "reason": f"Verification error: {str(e)}"}
    
    def load_blockchain(self):
        """Load blockchain from file"""
        try:
            os.makedirs(os.path.dirname(self.blockchain_file), exist_ok=True)
            
            if os.path.exists(self.blockchain_file):
                with open(self.blockchain_file, 'r') as f:
                    self.chain = json.load(f)
            else:
                # Create genesis block
                genesis = self.create_genesis_block()
                self.chain = [genesis]
                self.save_blockchain()
                
        except Exception as e:
            logging.error(f"Failed to load blockchain: {e}")
            # Create new blockchain with genesis block
            genesis = self.create_genesis_block()
            self.chain = [genesis]
    
    def save_blockchain(self):
        """Save blockchain to file"""
        try:
            os.makedirs(os.path.dirname(self.blockchain_file), exist_ok=True)
            with open(self.blockchain_file, 'w') as f:
                json.dump(self.chain, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save blockchain: {e}")
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        total_blocks = len(self.chain)
        total_transactions = sum(len(block["transactions"]) for block in self.chain)
        
        verified_invoices = BlockchainRecord.query.filter_by(
            record_type="invoice",
            verification_status="verified"
        ).count()
        
        return {
            "total_blocks": total_blocks,
            "total_transactions": total_transactions,
            "verified_invoices": verified_invoices,
            "chain_integrity": self.verify_chain_integrity(),
            "latest_block_time": self.chain[-1]["timestamp"] if self.chain else None
        }
    
    def verify_chain_integrity(self) -> bool:
        """Verify the entire blockchain integrity"""
        try:
            for i in range(1, len(self.chain)):
                current_block = self.chain[i]
                previous_block = self.chain[i-1]
                
                # Verify current block hash
                if current_block["hash"] != self.calculate_hash(current_block):
                    return False
                
                # Verify link to previous block
                if current_block["previous_hash"] != previous_block["hash"]:
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Chain integrity verification failed: {e}")
            return False

class SmartContractManager:
    """Manage smart contracts for automated payments and escrow"""
    
    def __init__(self):
        self.contracts = {}
    
    def create_payment_release_contract(self, invoice_id: int, conditions: Dict[str, Any]) -> str:
        """Create a smart contract for automatic payment release"""
        try:
            contract_id = f"payment_release_{invoice_id}_{int(time.time())}"
            
            contract_data = {
                "contract_id": contract_id,
                "type": "payment_release",
                "invoice_id": invoice_id,
                "conditions": conditions,
                "status": "active",
                "created_at": datetime.utcnow().isoformat(),
                "execution_rules": {
                    "auto_release_on_delivery": conditions.get("auto_release_on_delivery", False),
                    "escrow_period_days": conditions.get("escrow_period_days", 0),
                    "required_confirmations": conditions.get("required_confirmations", 1)
                }
            }
            
            # Save to database
            smart_contract = SmartContract(
                contract_address=contract_id,
                contract_type="payment_release",
                invoice_id=invoice_id,
                conditions=conditions,
                status="active"
            )
            db.session.add(smart_contract)
            db.session.commit()
            
            self.contracts[contract_id] = contract_data
            
            logging.info(f"Smart contract created: {contract_id}")
            return contract_id
            
        except Exception as e:
            logging.error(f"Failed to create smart contract: {e}")
            return ""
    
    def execute_contract(self, contract_id: str, trigger_data: Dict[str, Any]) -> bool:
        """Execute smart contract based on trigger conditions"""
        try:
            contract = SmartContract.query.filter_by(contract_address=contract_id).first()
            if not contract or contract.status != "active":
                return False
            
            conditions = contract.conditions
            execution_rules = conditions.get("execution_rules", {})
            
            # Check if execution conditions are met
            can_execute = True
            execution_log = []
            
            if execution_rules.get("auto_release_on_delivery") and trigger_data.get("delivery_confirmed"):
                execution_log.append("Delivery confirmed - condition met")
            elif execution_rules.get("escrow_period_days"):
                # Check if escrow period has passed
                escrow_end = contract.created_at + timedelta(days=execution_rules["escrow_period_days"])
                if datetime.utcnow() >= escrow_end:
                    execution_log.append("Escrow period completed - condition met")
                else:
                    can_execute = False
                    execution_log.append("Escrow period not yet completed")
            
            if can_execute:
                # Execute the contract
                contract.status = "executed"
                contract.executed_at = datetime.utcnow()
                contract.execution_data = {
                    "trigger_data": trigger_data,
                    "execution_log": execution_log,
                    "executed_at": datetime.utcnow().isoformat()
                }
                
                # Update related invoice if needed
                if contract.invoice_id:
                    invoice = Invoice.query.get(contract.invoice_id)
                    if invoice and trigger_data.get("mark_as_paid"):
                        invoice.payment_status = "Paid"
                        invoice.payment_date = datetime.utcnow().date()
                        invoice.payment_mode = "Smart Contract"
                        invoice.amount_paid = invoice.total_amount
                
                db.session.commit()
                
                logging.info(f"Smart contract executed: {contract_id}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Smart contract execution failed: {e}")
            return False

def initialize_blockchain():
    """Initialize blockchain services"""
    try:
        global blockchain_service, smart_contract_manager
        blockchain_service = BlockchainInvoiceVerification()
        smart_contract_manager = SmartContractManager()
        
        # Verify blockchain integrity on startup
        if not blockchain_service.verify_chain_integrity():
            logging.warning("Blockchain integrity check failed - reinitializing")
            blockchain_service = BlockchainInvoiceVerification()
        
        logging.info("Blockchain services initialized successfully")
        return True
        
    except Exception as e:
        logging.error(f"Failed to initialize blockchain services: {e}")
        return False

# Global blockchain service instances
blockchain_service = None
smart_contract_manager = None
