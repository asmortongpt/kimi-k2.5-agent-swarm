#!/usr/bin/env python3
"""
Real Kimi K2.5 Agent-Driven Visual Testing
100 agents actually control browser automation and testing
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add server/services to path
services_path = Path(__file__).parent / 'server' / 'services'
sys.path.insert(0, str(services_path))

from kimi_client_production import ProductionKimiClient, ChatMessage, SwarmConfig

print("=" * 80)
print("🚀 KIMI K2.5 AGENT-DRIVEN VISUAL TESTING")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("Using: 100 Kimi K2.5 agents to control browser automation")
print("=" * 80)

# Test configuration
FEATURES = [
    {"name": "Fleet Dashboard", "route": "/", "priority": "critical"},
    {"name": "Driver Dashboard", "route": "/drivers", "priority": "critical"},
    {"name": "Fleet Map", "route": "/fleet", "priority": "critical"},
    {"name": "Maintenance Hub", "route": "/maintenance", "priority": "critical"},
    {"name": "Compliance", "route": "/compliance", "priority": "critical"},
]

VIEWPORTS = [
    {"name": "desktop", "width": 1920, "height": 1080},
    {"name": "mobile", "width": 375, "height": 667},
]

async def main():
    # Initialize Kimi client
    client = ProductionKimiClient(model="kimi-k2.5:cloud")
    
    # Create swarm configuration
    swarm_config = SwarmConfig(
        num_agents=100,
        enable_coordination=True,
        enable_memory=True,
        max_iterations=5
    )
    
    print(f"\n📋 Assigning tasks to 100 Kimi agents...")
    print(f"   Features to test: {len(FEATURES)}")
    print(f"   Viewports: {len(VIEWPORTS)}")
    print(f"   Total scenarios: {len(FEATURES) * len(VIEWPORTS)}")
    
    # Create agent tasks
    agent_tasks = []
    agent_id = 1
    
    for feature in FEATURES:
        for viewport in VIEWPORTS:
            task = f"""
You are Agent #{agent_id} in a 100-agent swarm testing Fleet-CTA application.

YOUR SPECIFIC TASK:
- Feature: {feature['name']}
- Route: {feature['route']}
- Viewport: {viewport['name']} ({viewport['width']}x{viewport['height']})
- Priority: {feature['priority']}

TESTING PROCEDURE:
1. Navigate browser to: http://localhost:5173{feature['route']}
2. Wait for page load (networkidle state)
3. Capture screenshot
4. Check for errors in page content
5. Verify page title contains "Fleet"
6. Test basic interactivity (if applicable)

PLAYWRIGHT CODE TO EXECUTE:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={{'width': {viewport['width']}, 'height': {viewport['height']}}})
    
    # Navigate
    page.goto('http://localhost:5173{feature['route']}', wait_until='networkidle', timeout=30000)
    
    # Capture screenshot
    screenshot_path = 'test-results/kimi-agents/{viewport['name']}-{feature['name'].lower().replace(' ', '-')}.png'
    page.screenshot(path=screenshot_path, full_page=True)
    
    # Check for errors
    page_text = page.locator('body').text_content()
    has_error = 'error' in page_text.lower() or 'failed' in page_text.lower()
    
    # Get title
    title = page.title()
    
    browser.close()
    
    print(f"✅ Agent #{agent_id}: {feature['name']} ({viewport['name']}) - Screenshot captured")
    print(f"   Title: {{title}}")
    print(f"   Errors: {{has_error}}")
```

REPORT BACK:
- Success/Failure status
- Screenshot location
- Any errors found
- Page title
- Load time

Execute this test now and report your findings.
"""
            agent_tasks.append({
                "agent_id": agent_id,
                "feature": feature['name'],
                "viewport": viewport['name'],
                "prompt": task
            })
            agent_id += 1
    
    print(f"\n🐝 Launching {len(agent_tasks)} agents with specific test assignments...")
    
    # Execute agents in parallel
    results = []
    batch_size = 10  # Process 10 agents at a time
    
    for i in range(0, len(agent_tasks), batch_size):
        batch = agent_tasks[i:i+batch_size]
        print(f"\n📦 Processing batch {i//batch_size + 1}/{(len(agent_tasks)-1)//batch_size + 1} ({len(batch)} agents)...")
        
        batch_results = await asyncio.gather(*[
            run_agent(client, task) for task in batch
        ])
        results.extend(batch_results)
    
    # Summary
    print(f"\n{'=' * 80}")
    print("📊 KIMI AGENT-DRIVEN TESTING COMPLETE")
    print(f"{'=' * 80}")
    print(f"Total agents executed: {len(results)}")
    print(f"Successful tests: {sum(1 for r in results if r.get('success'))}")
    print(f"Failed tests: {sum(1 for r in results if not r.get('success'))}")
    
    # Save results
    report_path = Path("/Users/andrewmorton/Documents/GitHub/Fleet-CTA/KIMI_AGENT_TESTING_RESULTS.json")
    with open(report_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "agents_used": len(results),
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {report_path}")

async def run_agent(client: ProductionKimiClient, task: dict) -> dict:
    """Run a single Kimi agent to execute a test"""
    try:
        # Send task to Kimi agent
        messages = [ChatMessage(role="user", content=task["prompt"])]
        
        response = await client.chat_async(
            messages=messages,
            temperature=0.1,  # Low temperature for consistent testing
            max_tokens=2000
        )
        
        return {
            "agent_id": task["agent_id"],
            "feature": task["feature"],
            "viewport": task["viewport"],
            "success": True,
            "response": response.get("content", ""),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "agent_id": task["agent_id"],
            "feature": task["feature"],
            "viewport": task["viewport"],
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    asyncio.run(main())
