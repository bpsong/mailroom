# QR Code Generator for Package Tracking
# Main application file

from fastapi import FastAPI, Request, Form
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from io import BytesIO
import base64
import uuid
import qrcode
from qrcode.constants import ERROR_CORRECT_H
import logging
from pydantic import BaseModel, ValidationError, validator
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CM_TO_INCH = 1 / 2.54
TARGET_QR_CM = 2.0
PRINT_DPI = 300
TARGET_QR_PIXELS = int(TARGET_QR_CM * CM_TO_INCH * PRINT_DPI)

app = FastAPI()

# Configure Jinja2 templates
templates = Jinja2Templates(directory="qr_generator/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="qr_generator/static"), name="static")


def validate_uuid(uuid_string: str) -> bool:
    """
    Validates if the provided string is a valid UUID format.
    
    Args:
        uuid_string: The string to validate as UUID
        
    Returns:
        bool: True if valid UUID format, False otherwise
    """
    try:
        # Handle None or empty strings
        if not uuid_string or not isinstance(uuid_string, str):
            return False
        
        # Strip whitespace before validation
        uuid_string = uuid_string.strip()
        
        # Validate UUID format
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class UUIDInput(BaseModel):
    """
    Pydantic model for validating and normalizing UUID form input.
    """
    uuid: str

    @validator('uuid')
    def validate_uuid_format(cls, value: str) -> str:
        if value is None:
            raise ValueError("UUID is required.")
        if not isinstance(value, str):
            value = str(value)
        cleaned_value = value.strip()
        if not validate_uuid(cleaned_value):
            raise ValueError("Invalid UUID format.")
        return cleaned_value


class QRCodeResponse(BaseModel):
    """
    Structured response model for QR code generation results.
    """
    uuid: str
    tracking_url: str
    qr_code_base64: str


def create_tracking_url(package_uuid: str) -> str:
    """
    Creates a tracking URL for the given package UUID.
    
    Args:
        package_uuid: The package UUID to include in the URL
        
    Returns:
        str: The formatted tracking URL
    """
    return f"http://localhost:8000/packages/{package_uuid}"


def generate_qr_code(package_uuid: str) -> BytesIO:
    """
    Generates a QR code image for the given package UUID.
    
    The QR code encodes the tracking URL and is configured with:
    - High error correction (ERROR_CORRECT_H)
    - Box size tuned for compact stickers
    - Border of 4 boxes
    
    Args:
        package_uuid: The package UUID to encode in the QR code
        
    Returns:
        BytesIO: PNG image data as a BytesIO object
    """
    # Create tracking URL
    tracking_url = create_tracking_url(package_uuid)
    
    # Configure QR code according to design specs
    qr = qrcode.QRCode(
        version=None,  # Auto-detect optimal version
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    # Add data and generate
    qr.add_data(tracking_url)
    qr.make(fit=True)
    
    # Create image and normalize to 2cm x 2cm at 300 DPI
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize(
        (TARGET_QR_PIXELS, TARGET_QR_PIXELS),
        resample=Image.NEAREST
    )
    
    # Save to BytesIO with DPI metadata for print accuracy
    img_io = BytesIO()
    img.save(img_io, format='PNG', dpi=(PRINT_DPI, PRINT_DPI))
    img_io.seek(0)
    
    return img_io


# Routes

@app.get("/")
async def index(request: Request):
    """
    Renders the main form page for QR code generation.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        TemplateResponse: Rendered index.html template
    """
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}", exc_info=True)
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "An unexpected error occurred. Please try again."
            }
        )


@app.post("/generate")
async def generate(request: Request, uuid: str = Form(...)):
    """
    Generates a QR code for the provided package UUID.
    
    Args:
        request: FastAPI Request object
        uuid: Package UUID from form data
        
    Returns:
        TemplateResponse: Rendered template with QR code or error message
    """
    normalized_uuid = None
    submitted_uuid = uuid.strip() if isinstance(uuid, str) else uuid
    try:
        # Validate and normalize UUID input using Pydantic model
        uuid_input = UUIDInput(uuid=uuid)
        normalized_uuid = uuid_input.uuid
        
        # Generate QR code
        qr_code_io = generate_qr_code(normalized_uuid)
        
        # Encode to base64
        qr_code_base64 = base64.b64encode(qr_code_io.getvalue()).decode('utf-8')
        
        # Create tracking URL
        tracking_url = create_tracking_url(normalized_uuid)
        
        qr_response = QRCodeResponse(
            uuid=normalized_uuid,
            tracking_url=tracking_url,
            qr_code_base64=qr_code_base64
        )
        
        logger.info(f"Successfully generated QR code for UUID: {normalized_uuid}")
        
        # Render template with QR code data
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "uuid": qr_response.uuid,
                "qr_code_data": qr_response.qr_code_base64,
                "tracking_url": qr_response.tracking_url,
                "qr_response": qr_response
            }
        )
        
    except ValidationError:
        sanitized_uuid = submitted_uuid if submitted_uuid is not None else ""
        logger.warning(f"Invalid UUID format submitted: {sanitized_uuid}")
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Invalid UUID format. Please enter a valid UUID.",
                "uuid": sanitized_uuid
            }
        )
    except Exception as e:
        # Log the exception for debugging with full stack trace
        logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
        
        # Return user-friendly error message
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Failed to generate QR code. Please try again.",
                "uuid": normalized_uuid or submitted_uuid
            }
        )


@app.get("/download/{uuid}")
async def download(uuid: str):
    """
    Generates and downloads a QR code PNG file for the provided UUID.
    
    Args:
        uuid: Package UUID from path parameter
        
    Returns:
        Response: PNG image with attachment header for download
    """
    normalized_uuid = None
    submitted_uuid = uuid.strip() if isinstance(uuid, str) else uuid
    try:
        uuid_input = UUIDInput(uuid=uuid)
        normalized_uuid = uuid_input.uuid
        
        # Generate QR code
        qr_code_io = generate_qr_code(normalized_uuid)
        
        logger.info(f"Successfully generated QR code download for UUID: {normalized_uuid}")
        
        # Return as downloadable PNG file
        return Response(
            content=qr_code_io.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=qr_code_{normalized_uuid}.png"
            }
        )
    except ValidationError:
        logger.warning(f"Invalid UUID format in download request: {submitted_uuid}")
        return Response(
            content="Invalid UUID format",
            status_code=400,
            media_type="text/plain"
        )
    except Exception as e:
        # Log the exception for debugging with full stack trace
        logger.error(f"Error generating QR code for download: {str(e)}", exc_info=True)
        
        # Return error response
        return Response(
            content="Failed to generate QR code",
            status_code=500,
            media_type="text/plain"
        )
