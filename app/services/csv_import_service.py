"""CSV import service for bulk recipient imports."""

import csv
import io
import json
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.models import RecipientCreate, User
from app.services.recipient_service import recipient_service
from app.services.audit_service import audit_service
from app.database.write_queue import get_write_queue


class ImportValidationError:
    """Represents a validation error for a CSV row."""
    
    def __init__(self, row_number: int, field: str, message: str):
        self.row_number = row_number
        self.field = field
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "row": self.row_number,
            "field": self.field,
            "message": self.message,
        }


class ImportResult:
    """Result of a CSV import operation."""
    
    def __init__(self):
        self.total_rows = 0
        self.created_count = 0
        self.updated_count = 0
        self.error_count = 0
        self.errors: List[ImportValidationError] = []
        self.warnings: List[str] = []
    
    def add_error(self, row_number: int, field: str, message: str):
        """Add a validation error."""
        self.errors.append(ImportValidationError(row_number, field, message))
        self.error_count += 1
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "error_count": self.error_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
        }


class CSVImportService:
    """Service for importing recipients from CSV files."""
    
    REQUIRED_HEADERS = ["employee_id", "name", "email", "department"]
    OPTIONAL_HEADERS = ["phone", "location"]
    MAX_ROWS = 1000
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_headers(self, headers: List[str]) -> tuple[bool, Optional[str]]:
        """
        Validate CSV headers.
        
        Args:
            headers: List of header names from CSV
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for required headers
        missing_headers = []
        for required in self.REQUIRED_HEADERS:
            if required not in headers:
                missing_headers.append(required)
        
        if missing_headers:
            return False, f"Missing required columns: {', '.join(missing_headers)}"
        
        return True, None
    
    def _validate_row(
        self,
        row: Dict[str, str],
        row_number: int,
        result: ImportResult,
    ) -> Optional[RecipientCreate]:
        """
        Validate a single CSV row.
        
        Args:
            row: Dictionary of row data
            row_number: Row number for error reporting
            result: ImportResult to add errors to
            
        Returns:
            RecipientCreate object if valid, None if invalid
        """
        has_errors = False
        
        # Validate employee_id
        employee_id = row.get("employee_id", "").strip()
        if not employee_id:
            result.add_error(row_number, "employee_id", "Employee ID is required")
            has_errors = True
        elif len(employee_id) > 50:
            result.add_error(row_number, "employee_id", "Employee ID must be 50 characters or less")
            has_errors = True
        
        # Validate name
        name = row.get("name", "").strip()
        if not name:
            result.add_error(row_number, "name", "Name is required")
            has_errors = True
        elif len(name) > 100:
            result.add_error(row_number, "name", "Name must be 100 characters or less")
            has_errors = True
        
        # Validate email
        email = row.get("email", "").strip()
        if not email:
            result.add_error(row_number, "email", "Email is required")
            has_errors = True
        elif not self._validate_email(email):
            result.add_error(row_number, "email", f"Invalid email format: {email}")
            has_errors = True
        
        # Validate department
        department = row.get("department", "").strip()
        if not department:
            result.add_error(row_number, "department", "Department is required")
            has_errors = True
        elif len(department) > 100:
            result.add_error(row_number, "department", "Department must be 100 characters or less")
            has_errors = True
        
        # Validate optional fields
        phone = row.get("phone", "").strip() or None
        if phone and len(phone) > 20:
            result.add_error(row_number, "phone", "Phone must be 20 characters or less")
            has_errors = True
        
        location = row.get("location", "").strip() or None
        if location and len(location) > 100:
            result.add_error(row_number, "location", "Location must be 100 characters or less")
            has_errors = True
        
        if has_errors:
            return None
        
        # Create recipient data object
        return RecipientCreate(
            employee_id=employee_id,
            name=name,
            email=email,
            department=department,
            phone=phone,
            location=location,
        )
    
    async def parse_and_validate_csv(
        self,
        file_content: bytes,
    ) -> tuple[ImportResult, List[RecipientCreate]]:
        """
        Parse and validate CSV file (dry-run mode).
        
        Args:
            file_content: Raw CSV file content
            
        Returns:
            Tuple of (ImportResult, list of valid RecipientCreate objects)
        """
        result = ImportResult()
        valid_recipients = []
        
        try:
            # Decode file content
            content = file_content.decode('utf-8')
            csv_file = io.StringIO(content)
            
            # Parse CSV
            reader = csv.DictReader(csv_file)
            
            # Validate headers
            if not reader.fieldnames:
                result.add_error(0, "headers", "CSV file is empty or has no headers")
                return result, valid_recipients
            
            is_valid, error_msg = self._validate_headers(reader.fieldnames)
            if not is_valid:
                result.add_error(0, "headers", error_msg)
                return result, valid_recipients
            
            # Validate each row
            row_number = 1  # Start at 1 (header is row 0)
            for row in reader:
                row_number += 1
                result.total_rows += 1
                
                # Check max rows limit
                if result.total_rows > self.MAX_ROWS:
                    result.add_error(
                        row_number,
                        "file",
                        f"File exceeds maximum of {self.MAX_ROWS} rows",
                    )
                    break
                
                # Validate row
                recipient_data = self._validate_row(row, row_number, result)
                if recipient_data:
                    valid_recipients.append(recipient_data)
        
        except UnicodeDecodeError:
            result.add_error(0, "file", "File encoding error. Please use UTF-8 encoding")
        except csv.Error as e:
            result.add_error(0, "file", f"CSV parsing error: {str(e)}")
        except Exception as e:
            result.add_error(0, "file", f"Unexpected error: {str(e)}")
        
        return result, valid_recipients
    
    async def import_recipients(
        self,
        recipients: List[RecipientCreate],
        actor: User,
        filename: str = "import.csv",
    ) -> ImportResult:
        """
        Import recipients into database (upsert logic).
        
        Args:
            recipients: List of validated recipient data
            actor: User performing the import
            
        Returns:
            ImportResult with counts of created/updated records
        """
        result = ImportResult()
        result.total_rows = len(recipients)
        
        # Get existing employee IDs for upsert logic
        existing_employee_ids = set()
        for recipient_data in recipients:
            existing = await recipient_service.get_recipient_by_employee_id(
                recipient_data.employee_id
            )
            if existing:
                existing_employee_ids.add(recipient_data.employee_id)
        
        # Process each recipient
        for recipient_data in recipients:
            try:
                if recipient_data.employee_id in existing_employee_ids:
                    # Update existing recipient
                    existing = await recipient_service.get_recipient_by_employee_id(
                        recipient_data.employee_id
                    )
                    if existing:
                        from app.models import RecipientUpdate
                        update_data = RecipientUpdate(
                            name=recipient_data.name,
                            email=recipient_data.email,
                            department=recipient_data.department,
                            phone=recipient_data.phone,
                            location=recipient_data.location,
                        )
                        await recipient_service.update_recipient(
                            existing.id,
                            update_data,
                        )
                        result.updated_count += 1
                else:
                    # Create new recipient
                    await recipient_service.create_recipient(recipient_data)
                    result.created_count += 1
            
            except Exception as e:
                result.add_error(0, "import", f"Failed to import {recipient_data.employee_id}: {str(e)}")
        
        # Log import event
        await audit_service.log_recipient_import(
            actor_id=actor.id,
            filename=filename,
            records_created=result.created_count,
            records_updated=result.updated_count,
            errors=result.error_count,
        )
        
        return result


# Global CSV import service instance
csv_import_service = CSVImportService()
