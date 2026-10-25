"""Integration tests for injector free-text scenario parsing."""
import pytest
from jarvis.agent import injector


class TestInjectorParsing:
    """Test that injector.parse() extracts real parameters from free text."""
    
    def test_parse_merchant_and_amount(self):
        """Should extract merchant name exactly as typed."""
        template, params = injector.parse("Nordstrom $250 on Maya's card")
        
        assert template == "personal_card"
        assert params["amount"] == 250.00
        assert params["merchant"] == "Nordstrom"  # NOT "SEPHORA"
    
    def test_parse_date_formats(self):
        """Should parse various date formats."""
        # Format: 9/14
        template, params = injector.parse("Nordstrom $250 on 9/14")
        assert params["date"] == "2026-09-14"
        
        # Format: Sept 15
        template, params = injector.parse("$5000 wire on Sept 15")
        assert params["date"] == "2026-09-15"
        
        # Format: September 28
        template, params = injector.parse("Payment on September 28")
        assert params["date"] == "2026-09-28"
    
    def test_parse_cardholder(self):
        """Should extract cardholder from text."""
        template, params = injector.parse("$250 Nordstrom, cardholder J. Ortiz")
        
        assert params["cardholder"] == "J. Ortiz"
    
    def test_parse_vendor_in_quotes(self):
        """Should extract vendor from quoted text."""
        template, params = injector.parse("Wire from 'R&D Ventures LLC' for $5000")
        
        assert params["merchant"] == "R&D Ventures LLC"
        assert params["amount"] == 5000.00
    
    def test_bank_details_scenario(self):
        """Should recognize vendor bank-detail change scenario."""
        template, params = injector.parse(
            "Lumen emailed new bank details from lumencrew.co before the $18,400 payment"
        )
        
        # Should classify as vendor_bank_change
        assert template in ("vendor_bank_change", "invoice_over_accrual")
        assert "amount" in params
    
    def test_duplicate_detection(self):
        """Should recognize duplicate bill scenario."""
        template, params = injector.parse(
            "Notion sent two bills for $96 each in September"
        )
        
        assert template == "duplicate_bill"
        assert params["amount"] == 96.00
    
    def test_personal_purchase_keywords(self):
        """Should recognize personal purchase keywords."""
        # Nordstrom
        template, _ = injector.parse("Nordstrom $150")
        assert template == "personal_card"
        
        # Sephora
        template, _ = injector.parse("Sephora $89.50")
        assert template == "personal_card"
        
        # Steam/games
        template, _ = injector.parse("Steam purchase $45")
        assert template == "personal_card"
    
    def test_refund_scenario(self):
        """Should recognize refund booked as revenue."""
        template, params = injector.parse(
            "Bank shows +$1,200 refund from Bay Rig Rentals"
        )
        
        # Should detect refund
        assert "refund" in template.lower() or template == "unknown_debit"
        assert params["amount"] == 1200.00
    
    def test_ghost_vendor(self):
        """Should recognize ghost vendor scenario."""
        template, params = injector.parse(
            "Payment to 'Advanced Solutions Inc' for $8,500 but vendor doesn't exist"
        )
        
        assert template in ("ghost_vendor", "unknown_debit")
        assert params["amount"] == 8500.00
    
    def test_split_purchases(self):
        """Should recognize split purchases under threshold."""
        template, params = injector.parse(
            "Three Office Depot purchases: $245, $235, $240, all under threshold"
        )
        
        # Should recognize split or multiple purchases
        assert template in ("split_purchases", "unknown_debit")
    
    def test_amount_extraction_variations(self):
        """Should handle various amount formats."""
        # With comma
        _, params = injector.parse("Wire for $5,000")
        assert params["amount"] == 5000.00
        
        # With cents
        _, params = injector.parse("Charge of $96.40")
        assert params["amount"] == 96.40
        
        # No dollar sign
        _, params = injector.parse("Payment 2500 dollars")
        # May or may not extract, but shouldn't break
        assert "amount" in params


class TestInjectorTemplates:
    """Test that new templates are defined."""
    
    def test_new_templates_exist(self):
        """Should have all required templates."""
        required = [
            "unknown_debit",
            "personal_card", 
            "duplicate_bill",
            "paypal_bundle",
            "invoice_over_accrual",
            "vendor_bank_change",
            "split_purchases",
            "ghost_vendor",
            "refund_as_revenue"
        ]
        
        for template in required:
            assert template in injector.TEMPLATES, f"Missing template: {template}"
            assert "label" in injector.TEMPLATES[template]
            assert "params" in injector.TEMPLATES[template]
