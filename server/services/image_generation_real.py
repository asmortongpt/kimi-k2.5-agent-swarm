#!/usr/bin/env python3
"""
Real Image Generation - NO MOCKS
Supports multiple backends: Stable Diffusion, PIL/Pillow, matplotlib
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import base64
from io import BytesIO


class ImageGenerationBackend(Enum):
    """Available image generation backends"""
    STABLE_DIFFUSION = "stable_diffusion"  # AI-generated images
    PROGRAMMATIC = "programmatic"  # Algorithmic/code-based
    MATPLOTLIB = "matplotlib"  # Charts and visualizations


@dataclass
class ImageResult:
    """Result from image generation"""
    success: bool
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    error: Optional[str] = None
    generation_time_ms: int = 0
    metadata: Dict[str, Any] = None


class RealImageGenerator:
    """
    Real image generation - NO SIMULATION
    Uses actual models and libraries
    """

    def __init__(self, backend: ImageGenerationBackend = ImageGenerationBackend.PROGRAMMATIC):
        self.backend = backend
        self.output_dir = Path("/tmp/kimi_generated_images")
        self.output_dir.mkdir(exist_ok=True)

        # Initialize backends on demand
        self._sd_pipeline = None
        self._plt = None
        self._pil = None

    def _init_stable_diffusion(self):
        """Initialize Stable Diffusion pipeline (lazy loading)"""
        if self._sd_pipeline is None:
            try:
                from diffusers import StableDiffusionPipeline
                import torch

                print("Loading Stable Diffusion model (this may take a minute)...")

                # Use a lightweight model for local generation
                model_id = "stabilityai/stable-diffusion-2-1-base"

                self._sd_pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    safety_checker=None  # Disable for speed
                )

                # Move to GPU if available
                if torch.cuda.is_available():
                    self._sd_pipeline = self._sd_pipeline.to("cuda")
                else:
                    # Use CPU with reduced precision for speed
                    self._sd_pipeline = self._sd_pipeline.to("cpu")

                print("✅ Stable Diffusion loaded")

            except ImportError:
                raise ImportError(
                    "Stable Diffusion not available. Install with: "
                    "pip install diffusers transformers torch"
                )

    def _init_matplotlib(self):
        """Initialize matplotlib (lazy loading)"""
        if self._plt is None:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            self._plt = plt

    def _init_pil(self):
        """Initialize PIL/Pillow (lazy loading)"""
        if self._pil is None:
            from PIL import Image, ImageDraw, ImageFont
            self._pil = {"Image": Image, "ImageDraw": ImageDraw, "ImageFont": ImageFont}

    async def generate_from_text(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        output_path: Optional[str] = None
    ) -> ImageResult:
        """
        Generate image from text using Stable Diffusion
        REAL AI generation - NO MOCKS
        """
        start = datetime.utcnow()

        try:
            # Initialize Stable Diffusion
            self._init_stable_diffusion()

            # Generate filename if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(self.output_dir / f"sd_{timestamp}.png")

            # Actually generate the image
            print(f"Generating image: {prompt[:50]}...")

            image = self._sd_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]

            # Save image
            image.save(output_path)

            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            generation_time = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ImageResult(
                success=True,
                image_path=output_path,
                image_base64=img_base64,
                generation_time_ms=generation_time,
                metadata={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "backend": "stable_diffusion"
                }
            )

        except Exception as e:
            return ImageResult(
                success=False,
                error=f"Stable Diffusion generation failed: {str(e)}"
            )

    async def generate_programmatic(
        self,
        image_type: Literal["gradient", "pattern", "shapes", "text"],
        params: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> ImageResult:
        """
        Generate images programmatically using PIL
        REAL image creation - NO MOCKS
        """
        start = datetime.utcnow()

        try:
            self._init_pil()
            Image = self._pil["Image"]
            ImageDraw = self._pil["ImageDraw"]

            # Generate filename if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(self.output_dir / f"prog_{image_type}_{timestamp}.png")

            width = params.get("width", 512)
            height = params.get("height", 512)

            # Actually create the image
            if image_type == "gradient":
                image = Image.new("RGB", (width, height))
                pixels = image.load()
                for y in range(height):
                    for x in range(width):
                        r = int((x / width) * 255)
                        g = int((y / height) * 255)
                        b = 128
                        pixels[x, y] = (r, g, b)

            elif image_type == "pattern":
                image = Image.new("RGB", (width, height), color="white")
                draw = ImageDraw.Draw(image)
                spacing = params.get("spacing", 20)
                color = params.get("color", "blue")

                for x in range(0, width, spacing):
                    draw.line([(x, 0), (x, height)], fill=color, width=2)
                for y in range(0, height, spacing):
                    draw.line([(0, y), (width, y)], fill=color, width=2)

            elif image_type == "shapes":
                image = Image.new("RGB", (width, height), color=params.get("bg_color", "white"))
                draw = ImageDraw.Draw(image)

                # Draw random shapes
                import random
                for _ in range(params.get("num_shapes", 10)):
                    x1, y1 = random.randint(0, width), random.randint(0, height)
                    x2, y2 = random.randint(0, width), random.randint(0, height)
                    color = tuple(random.randint(0, 255) for _ in range(3))

                    shape = random.choice(["rectangle", "ellipse"])
                    if shape == "rectangle":
                        draw.rectangle([x1, y1, x2, y2], fill=color, outline="black")
                    else:
                        draw.ellipse([x1, y1, x2, y2], fill=color, outline="black")

            elif image_type == "text":
                image = Image.new("RGB", (width, height), color=params.get("bg_color", "white"))
                draw = ImageDraw.Draw(image)
                text = params.get("text", "Generated by Kimi K2.5")
                position = params.get("position", (50, height // 2))
                color = params.get("text_color", "black")

                draw.text(position, text, fill=color)

            else:
                raise ValueError(f"Unknown image type: {image_type}")

            # Save image
            image.save(output_path)

            # Convert to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

            generation_time = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ImageResult(
                success=True,
                image_path=output_path,
                image_base64=img_base64,
                generation_time_ms=generation_time,
                metadata={
                    "type": image_type,
                    "params": params,
                    "backend": "programmatic"
                }
            )

        except Exception as e:
            return ImageResult(
                success=False,
                error=f"Programmatic generation failed: {str(e)}"
            )

    async def generate_chart(
        self,
        chart_type: Literal["line", "bar", "scatter", "pie"],
        data: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> ImageResult:
        """
        Generate charts and visualizations using matplotlib
        REAL chart generation - NO MOCKS
        """
        start = datetime.utcnow()

        try:
            self._init_matplotlib()
            plt = self._plt

            # Generate filename if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(self.output_dir / f"chart_{chart_type}_{timestamp}.png")

            # Actually create the chart
            fig, ax = plt.subplots(figsize=(10, 6))

            if chart_type == "line":
                x = data.get("x", list(range(len(data.get("y", [])))))
                y = data.get("y", [])
                ax.plot(x, y, marker='o')
                ax.set_xlabel(data.get("xlabel", "X"))
                ax.set_ylabel(data.get("ylabel", "Y"))

            elif chart_type == "bar":
                categories = data.get("categories", [])
                values = data.get("values", [])
                ax.bar(categories, values)
                ax.set_xlabel(data.get("xlabel", "Category"))
                ax.set_ylabel(data.get("ylabel", "Value"))

            elif chart_type == "scatter":
                x = data.get("x", [])
                y = data.get("y", [])
                ax.scatter(x, y)
                ax.set_xlabel(data.get("xlabel", "X"))
                ax.set_ylabel(data.get("ylabel", "Y"))

            elif chart_type == "pie":
                values = data.get("values", [])
                labels = data.get("labels", [])
                ax.pie(values, labels=labels, autopct='%1.1f%%')

            ax.set_title(data.get("title", f"{chart_type.title()} Chart"))
            ax.grid(data.get("grid", True))

            # Save figure
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            # Convert to base64
            with open(output_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode()

            generation_time = int((datetime.utcnow() - start).total_seconds() * 1000)

            return ImageResult(
                success=True,
                image_path=output_path,
                image_base64=img_base64,
                generation_time_ms=generation_time,
                metadata={
                    "chart_type": chart_type,
                    "backend": "matplotlib"
                }
            )

        except Exception as e:
            return ImageResult(
                success=False,
                error=f"Chart generation failed: {str(e)}"
            )


# Demonstration
async def demo_image_generation():
    """Demonstrate REAL image generation (not mocked)"""
    print("🎨 Real Image Generation Demo\n")

    generator = RealImageGenerator()

    # 1. Programmatic gradient
    print("1. Generating gradient...")
    result = await generator.generate_programmatic(
        "gradient",
        {"width": 400, "height": 400}
    )
    print(f"   {'✅' if result.success else '❌'} {result.image_path or result.error}\n")

    # 2. Pattern
    print("2. Generating pattern...")
    result = await generator.generate_programmatic(
        "pattern",
        {"width": 400, "height": 400, "spacing": 30, "color": "blue"}
    )
    print(f"   {'✅' if result.success else '❌'} {result.image_path or result.error}\n")

    # 3. Chart
    print("3. Generating chart...")
    result = await generator.generate_chart(
        "bar",
        {
            "categories": ["A", "B", "C", "D"],
            "values": [10, 25, 15, 30],
            "title": "Sample Data",
            "xlabel": "Category",
            "ylabel": "Value"
        }
    )
    print(f"   {'✅' if result.success else '❌'} {result.image_path or result.error}\n")

    # 4. Stable Diffusion (commented out by default - requires model download)
    # print("4. Generating AI image with Stable Diffusion...")
    # result = await generator.generate_from_text(
    #     "a beautiful sunset over mountains, highly detailed, 4k",
    #     negative_prompt="blurry, low quality",
    #     num_inference_steps=20
    # )
    # print(f"   {'✅' if result.success else '❌'} {result.image_path or result.error}\n")

    print(f"All generated images saved to: {generator.output_dir}")


if __name__ == "__main__":
    asyncio.run(demo_image_generation())
