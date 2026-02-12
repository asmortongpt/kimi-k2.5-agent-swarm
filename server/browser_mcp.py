from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
from pathlib import Path
import tempfile

app = FastAPI()

class BrowserToolCall(BaseModel):
    toolName: str
    input: Dict[str, Any]

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/tools")
def tools():
    return [
        {
            "name": "test_html",
            "description": "Test HTML with Playwright + visual diff",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "html": {"type": "string"},
                    "viewport": {"type": "object"},
                    "screenshots": {"type": "array"},
                    "visualDiff": {"type": "object"},
                    "checks": {"type": "array"}
                },
                "required": ["html"]
            }
        }
    ]

@app.post("/tools/call")
async def call_tool(req: BrowserToolCall):
    if req.toolName == "test_html":
        return await test_html(req.input)
    raise HTTPException(status_code=404, detail=f"Unknown tool: {req.toolName}")

async def test_html(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test HTML with Playwright
    Returns: screenshots, diffs, metrics, pass/fail
    """
    from playwright.async_api import async_playwright
    from PIL import Image, ImageChops
    import os

    html_content = params["html"]
    viewport = params.get("viewport", {"width": 1280, "height": 720})
    screenshots_config = params.get("screenshots", [])
    visual_diff_config = params.get("visualDiff", {})

    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        html_path = f.name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport=viewport)
            await page.goto(f'file://{html_path}')

            screenshot_paths = []
            diffs = []

            # Take screenshots
            for shot in screenshots_config:
                shot_name = shot.get("name", "screenshot")
                selector = shot.get("selector", "body")
                scroll_y = shot.get("scrollY", 0)

                if scroll_y > 0:
                    await page.evaluate(f"window.scrollTo(0, {scroll_y})")
                    await page.wait_for_timeout(500)

                shot_path = f'/tmp/screenshots/{shot_name}.png'
                os.makedirs(os.path.dirname(shot_path), exist_ok=True)

                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=shot_path)
                    screenshot_paths.append(shot_path)

                    # Visual diff if baseline exists
                    if visual_diff_config:
                        baseline_dir = visual_diff_config.get("baselineDir", ".visual-baseline")
                        baseline_path = f'{baseline_dir}/{shot_name}.png'

                        if os.path.exists(baseline_path):
                            # Compare with baseline
                            diff_result = compare_images(baseline_path, shot_path)
                            if diff_result["diff_percent"] > visual_diff_config.get("threshold", 0.02):
                                diff_dir = visual_diff_config.get("diffDir", ".visual-diffs")
                                diff_path = f'{diff_dir}/{shot_name}-diff.png'
                                os.makedirs(os.path.dirname(diff_path), exist_ok=True)
                                diff_result["diff_image"].save(diff_path)
                                diffs.append({
                                    "name": shot_name,
                                    "diff_percent": diff_result["diff_percent"],
                                    "diff_path": diff_path
                                })

            await browser.close()

            # Determine pass/fail
            passed = len(diffs) == 0

            return {
                "passed": passed,
                "screenshots": screenshot_paths,
                "diffs": diffs,
                "metrics": {
                    "screenshots_taken": len(screenshot_paths),
                    "diffs_found": len(diffs)
                }
            }

    finally:
        os.unlink(html_path)

def compare_images(baseline_path: str, current_path: str) -> Dict[str, Any]:
    """Compare two images pixel by pixel"""
    baseline = Image.open(baseline_path)
    current = Image.open(current_path)

    # Ensure same size
    if baseline.size != current.size:
        current = current.resize(baseline.size)

    # Calculate diff
    diff = ImageChops.difference(baseline, current)
    diff_pixels = sum(sum(1 for p in row if p != 0) for row in diff.getdata())
    total_pixels = baseline.size[0] * baseline.size[1]
    diff_percent = diff_pixels / total_pixels

    return {
        "diff_percent": diff_percent,
        "diff_image": diff
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
