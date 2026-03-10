import io
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Literal, Optional

from PIL import Image, ImageDraw
from pydantic import BaseModel

from khoj.processor.operator.operator_actions import OperatorAction, Point
from khoj.utils.helpers import convert_image_to_webp


logger = logging.getLogger(__name__)


class EnvironmentType(Enum):
    """Type of environment to operate."""

    COMPUTER = "computer"
    BROWSER = "browser"


class EnvState(BaseModel):
    height: int
    width: int
    screenshot: Optional[str] = None
    url: Optional[str] = None


class EnvStepResult(BaseModel):
    type: Literal["text", "image"] = "text"
    output: Optional[str | dict] = None
    error: Optional[str] = None
    current_url: Optional[str] = None
    screenshot_base64: Optional[str] = None


class Environment(ABC):
    @abstractmethod
    async def start(self, width: int, height: int) -> None:
        pass

    @abstractmethod
    async def step(self, action: OperatorAction) -> EnvStepResult:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def get_state(self) -> EnvState:
        pass

    @abstractmethod
    async def _get_screenshot_bytes(self) -> Optional[bytes]:
        """Get raw screenshot as bytes. Returns None if screenshot unavailable."""
        pass

    @abstractmethod
    def _get_mouse_position(self) -> Optional[Point]:
        """Get current mouse position."""
        pass

    async def _get_screenshot(self) -> Optional[str]:
        """Get screenshot as base64-encoded webp string with mouse position drawn."""
        try:
            screenshot_bytes = await self._get_screenshot_bytes()
            if screenshot_bytes is None:
                return None

            # Draw mouse position on the screenshot
            mouse_pos = self._get_mouse_position()
            if mouse_pos:
                screenshot_bytes = await self._draw_mouse_position(screenshot_bytes, mouse_pos)

            # Convert to webp and encode
            screenshot_webp_bytes = convert_image_to_webp(screenshot_bytes)
            import base64

            return base64.b64encode(screenshot_webp_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}", exc_info=True)
            return None

    async def _draw_mouse_position(self, screenshot_bytes: bytes, mouse_pos: Point, radius: int = 8) -> bytes:
        """Draw mouse position as a red circle on the screenshot."""
        try:
            image = Image.open(io.BytesIO(screenshot_bytes))
            draw = ImageDraw.Draw(image)

            # Red circle with black border for better visibility
            draw.ellipse(
                (mouse_pos.x - radius, mouse_pos.y - radius, mouse_pos.x + radius, mouse_pos.y + radius),
                outline="black",
                fill="red",
                width=2,
            )

            output_buffer = io.BytesIO()
            image.save(output_buffer, format="PNG")
            return output_buffer.getvalue()
        except Exception as e:
            logger.error(f"Failed to draw mouse position: {e}")
            return screenshot_bytes
