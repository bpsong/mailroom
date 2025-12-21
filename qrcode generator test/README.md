# QR Code Generator for Package Tracking

A lightweight web application that generates high-quality, printable QR codes for package tracking. Built with FastAPI and Python, this tool provides a simple interface for creating QR codes that encode package tracking URLs.

## Features

- Generate QR codes from package UUIDs
- High-quality QR codes with error correction
- Download QR codes as PNG files
- Print-friendly interface
- UUID validation and error handling
- Clean, responsive web interface

## Requirements

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone or download this repository

2. Install the required dependencies:

```powershell
pip install -r requirements.txt
```

The application requires the following packages:
- FastAPI - Web framework
- uvicorn - ASGI server
- qrcode[pil] - QR code generation with image support
- jinja2 - Template engine
- python-multipart - Form parsing required by FastAPI's `Form` dependencies

## Usage

### Starting the Application

Run the development server:

```powershell
uvicorn qr_generator.app:app --reload --port 8000
```

The application will be available at `http://localhost:8000`

### Generating QR Codes

1. Open your browser and navigate to `http://localhost:8000`

2. Enter a valid UUID in the "Package UUID" field
   - Example: `550e8400-e29b-41d4-a716-446655440000`

3. Click "Generate QR Code"

4. The QR code will be displayed along with:
   - The tracking URL preview
   - A download button to save the QR code as PNG
   - A print button to print the QR code

### Downloading QR Codes

Click the "Download QR Code" button to save the generated QR code as a PNG file. The file will be named `qr_code_{uuid}.png`.

### Printing QR Codes

Click the "Print QR Code" button to open the browser's print dialog. The interface is optimized for printing, hiding unnecessary elements and ensuring the QR code is clearly visible.

## QR Code Specifications

The generated QR codes have the following specifications:

- **Format**: PNG
- **Error Correction**: High (ERROR_CORRECT_H)
- **Box Size**: 10 pixels (generated at high resolution before resizing)
- **Border**: 4 boxes
- **Physical Size**: exactly 2cm x 2cm (PNG resized and saved with 300 DPI metadata)
- **Encoding**: Tracking URL in format `http://localhost:8000/packages/{uuid}`

These settings ensure reliable scanning in production environments.

## API Endpoints

### GET /
Displays the main form page for QR code generation.

### POST /generate
Generates a QR code for the provided UUID.

**Form Parameters:**
- `uuid` (required): Package UUID in valid UUID format

**Response:**
- HTML page with QR code image (base64-encoded)
- Error message if UUID is invalid

### GET /download/{uuid}
Downloads a QR code PNG file for the specified UUID.

**Path Parameters:**
- `uuid` (required): Package UUID

**Response:**
- PNG image file with Content-Disposition header for download
- 400 error if UUID is invalid
- 500 error if generation fails

## Project Structure

```
qr_generator/
├── app.py                 # Main FastAPI application
├── templates/
│   └── index.html        # Web interface template
└── static/
    └── styles.css        # CSS styling
requirements.txt          # Python dependencies
README.md                # This file
```

## Troubleshooting

### Application won't start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**: Ensure all dependencies are installed:
```powershell
pip install -r requirements.txt
```

**Problem**: Port 8000 is already in use

**Solution**: Use a different port:
```powershell
uvicorn qr_generator.app:app --reload --port 8080
```

### QR Code generation issues

**Problem**: "Invalid UUID format" error

**Solution**: Ensure you're entering a valid UUID format. Valid examples:
- `550e8400-e29b-41d4-a716-446655440000` (UUID v4)
- `6ba7b810-9dad-11d1-80b4-00c04fd430c8` (UUID v1)

**Problem**: QR code won't scan or prints at the wrong size

**Solution**: 
- Ensure the printed QR code is exactly 2cm x 2cm (browser print styles enforce this)
- Check that the print quality is sufficient
- Verify the QR code is not damaged or obscured
- Try adjusting the scanner distance

### Template or static file errors

**Problem**: Template not found or CSS not loading

**Solution**: Ensure you're running the application from the correct directory. The application expects the following structure:
- `qr_generator/templates/index.html`
- `qr_generator/static/styles.css`

Run the application using:
```powershell
uvicorn qr_generator.app:app --reload
```

### Browser compatibility

**Problem**: Print functionality not working

**Solution**: The print feature uses `window.print()` which is supported by all modern browsers. Ensure JavaScript is enabled in your browser.

**Problem**: QR code image not displaying

**Solution**: 
- Clear your browser cache
- Try a different browser (Chrome, Firefox, Safari, Edge)
- Check browser console for errors (F12)

## Production Deployment

For production use, consider the following:

1. **Use a production ASGI server**:
```powershell
pip install gunicorn
gunicorn qr_generator.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Update the tracking URL**: Modify the `create_tracking_url()` function in `app.py` to use your production domain instead of `localhost:8000`

3. **Configure logging**: Adjust logging levels in production for better performance

4. **Add rate limiting**: Consider implementing rate limiting to prevent abuse

5. **Use HTTPS**: Ensure your production deployment uses HTTPS for security

## Development

### Running in development mode

```powershell
uvicorn qr_generator.app:app --reload --port 8000
```

The `--reload` flag enables auto-reload on code changes.

### Logging

The application logs important events and errors. Logs include:
- Successful QR code generation
- Invalid UUID submissions
- Error details for debugging

Check the console output for log messages.

## License

This project is provided as-is for package tracking purposes.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the application logs for error details
3. Verify all requirements are properly installed
4. Ensure the project structure is intact

