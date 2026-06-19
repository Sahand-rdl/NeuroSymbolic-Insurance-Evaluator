import io
import base64
from PIL import Image

def process_and_encode_image(image_path: str, max_edge: int = 1024, quality: int = 85) -> str:
    """
    Opens an image using Pillow, proportionally resizes it if the longest edge exceeds max_edge,
    converts to RGB, compresses to JPEG, and returns the Base64 encoded string.
    This protects TPM/RPM limits and drastically reduces latency compared to raw 4K images.
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB to ensure compatibility with JPEG format
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Check dimensions and resize proportionally if necessary
            width, height = img.size
            if width > max_edge or height > max_edge:
                if width > height:
                    new_width = max_edge
                    new_height = int(max_edge * (height / width))
                else:
                    new_height = max_edge
                    new_width = int(max_edge * (width / height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to process image {image_path}: {str(e)}")
