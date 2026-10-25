"""Integration tests for workbench /api/wb/run endpoints.

Tests that every tab runs successfully through the workbench API.
"""
import pytest
from fastapi.testclient import TestClient
import time

# Import the FastAPI app
from jarvis.api import server

# Use TestClient instead of real server
@pytest.fixture(scope="module")
def client():
    """Create test client."""
    with TestClient(server.app) as c:
        yield c

TABS = [
    "p1_timing",
    "p2_rollforward",
    "p3_bank",
    "p4_evidence",
    "p5_vendors",
]


class TestWorkbenchRun:
    """Test /api/wb/run for each tab."""
    
    def test_p1_timing(self, client):
        """Test P1 Timing tab runs without failure."""
        resp = client.post("/api/wb/run", json={"agent": "p1_timing"})
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["problem"] == "p1_timing"
        assert data["status"] in ("running", "awaiting_approval", "done")
        
        # Wait for completion
        run_id = data["id"]
        for _ in range(60):  # Max 60 seconds
            time.sleep(0.1)  # Shorter sleep with TestClient
            status_resp = client.get(f"/api/wb/run/{run_id}")
            status_data = status_resp.json()
            
            if status_data["status"] in ("awaiting_approval", "done"):
                assert status_data["status"] != "failed", f"Run failed: {status_data.get('error')}"
                return
        
        pytest.fail("Run did not complete within 6 seconds")
    
    def test_p2_rollforward(self, client):
        """Test P2 Rollforward tab runs without failure."""
        resp = client.post("/api/wb/run", json={"agent": "p2_rollforward"})
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["problem"] == "p2_rollforward"
        assert data["status"] != "failed"
    
    def test_p3_bank(self, client):
        """Test P3 Bank tab runs without failure."""
        resp = client.post("/api/wb/run", json={"agent": "p3_bank"})
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["problem"] == "p3_bank"
        assert data["status"] != "failed"
    
    def test_p4_evidence(self, client):
        """Test P4 Evidence tab runs without failure."""
        resp = client.post("/api/wb/run", json={"agent": "p4_evidence"})
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["problem"] == "p4_evidence"
        assert data["status"] != "failed"
    
    def test_p5_vendors(self, client):
        """Test P5 Vendors tab runs without failure."""
        resp = client.post("/api/wb/run", json={"agent": "p5_vendors"})
        assert resp.status_code == 200
        
        data = resp.json()
        assert data["problem"] == "p5_vendors"
        assert data["status"] != "failed"


class TestWorkbenchValidation:
    """Additional validation tests."""
    
    def test_all_tabs_complete(self, client):
        """Test that all 5 tabs can complete successfully."""
        results = {}
        
        for tab in TABS:
            resp = client.post("/api/wb/run", json={"agent": tab})
            
            if resp.status_code != 200:
                results[tab] = f"HTTP {resp.status_code}"
                continue
            
            data = resp.json()
            run_id = data["id"]
            
            # Wait for completion (shorter with TestClient)
            for _ in range(60):
                time.sleep(0.1)
                status_resp = client.get(f"/api/wb/run/{run_id}")
                status_data = status_resp.json()
                
                if status_data["status"] in ("awaiting_approval", "done"):
                    results[tab] = "success"
                    break
                elif status_data["status"] == "failed":
                    results[tab] = f"failed: {status_data.get('error', 'unknown')}"
                    break
            else:
                results[tab] = "timeout"
        
        # Report results
        failures = {k: v for k, v in results.items() if v != "success"}
        assert not failures, f"Failed tabs: {failures}"
