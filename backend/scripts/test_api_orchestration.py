#!/usr/bin/env python3
"""Test API with connected orchestration"""
import requests
import json

url = "http://localhost:8000/api/cases/by-primaryid/182265253/analyze"
resp = requests.post(url, headers={"Content-Type": "application/json"})
data = resp.json()

analysis = data.get("analysis", data)

print("=" * 60)
print("CONNECTED ORCHESTRATION - API TEST")
print("=" * 60)

# Check for orchestration context
orch = analysis.get("orchestration_context", {})
if orch:
    print(f"Connected Flow: {orch.get('connected_flow', 'N/A')}")
    print(f"Execution Order: {orch.get('execution_order', [])}")
    print(f"Feature Status: {orch.get('feature_status', {})}")
else:
    print("No orchestration context (may be using fallback)")

print()
print("--- Feature-1 Outputs ---")
print(f"  Risk Score: {analysis.get('risk_score', 'N/A')}")
print(f"  Risk Category: {analysis.get('risk_category', 'N/A')}")

print()
print("--- Feature-2 Outputs ---")
print(f"  Decision: {analysis.get('decision', 'N/A')}")
print(f"  Priority: {analysis.get('followup_priority', 'N/A')}")

print()
print("--- Feature-3 Outputs ---")
questions = analysis.get("questions", [])
print(f"  Questions: {len(questions)}")
print(f"  Stop Followup: {analysis.get('stop_followup', 'N/A')}")
print()
print("API Test Complete")
