# CSRF Implementation Guide for Developers

This guide explains how to properly implement CSRF protection in the Mailroom Tracking System.

## Overview

CSRF (Cross-Site Request Forgery) protection is now enforced on all state-changing endpoints (POST, PUT, PATCH, DELETE). This guide shows you how to implement it correctly in your routes and templates.

## Quick Reference

### For HTMX/AJAX Requests
✓ CSRF token is automatically included via `X-CSRF-Token` header  
✓ No additional code needed in most cases

### For HTML Forms
✓ Include `csrf_token` hidden input field  
✓ Call `validate_csrf_token()` in route handler

---

## Implementation Methods

### Method 1: HTMX Requests (Recommended)

HTMX requests automatically include the CSRF token from the meta tag.

**Template (base.html already includes this):**
```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

**HTMX Configuration (base.html already includes this):**
```javascript
document.body.addEventListener('htmx:configRequest', function(event) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    if (csrfToken) {
        event.detail.headers['X-CSRF-Token'] = csrfToken.content;
    }
});
```

**Route Handler:**
```python
@router.post("/packages/{package_id}/status")
async def update_package_status(
    request: Request,
    package_id: str,
    status: str = Form(...),
):
    # CSRF is automatically validated by middleware for HTMX requests
    # No additional code needed
    
    # Your logic here
    await package_service.update_status(package_id, status)
    
    return {"success": True}
```

---

### Method 2: HTML Form Submissions

For traditional form submissions (non-HTMX), you must include the CSRF token as a hidden field.

**Template:**
```html
<form method="POST" action="/admin/users">
    <!-- Include CSRF token as hidden field -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    
    <input type="text" name="username" required>
    <input type="password" name="password" required>
    
    <button type="submit">Create User</button>
</form>
```

**Route Handler:**
```python
from app.middleware.csrf import validate_csrf_token

@router.post("/admin/users")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),  # Accept CSRF token from form
):
    # Validate CSRF token
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )
    
    # Your logic here
    user = await user_service.create_user(username, password)
    
    return {"success": True, "user_id": str(user.id)}
```

---

### Method 3: JavaScript Fetch/Axios

For custom JavaScript requests, include the CSRF token in the headers.

**JavaScript:**
```javascript
// Get CSRF token from meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

// Fetch API
fetch('/api/packages', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify({
        tracking_number: 'PKG123',
        recipient_id: 'abc-123',
    }),
});

// Axios
axios.post('/api/packages', {
    tracking_number: 'PKG123',
    recipient_id: 'abc-123',
}, {
    headers: {
        'X-CSRF-Token': csrfToken,
    },
});
```

**Route Handler:**
```python
@router.post("/api/packages")
async def create_package(
    request: Request,
    package_data: PackageCreate,
):
    # CSRF is automatically validated by middleware for requests with X-CSRF-Token header
    # No additional code needed
    
    # Your logic here
    package = await package_service.create_package(package_data)
    
    return {"success": True, "package_id": str(package.id)}
```

---

## Passing CSRF Token to Templates

All template responses must include the CSRF token in the context.

**Using Helper Function (Recommended):**
```python
from app.utils.csrf_helpers import add_csrf_to_context

@router.get("/packages/new")
async def new_package_form(request: Request):
    user = get_current_user(request)
    
    context = {
        "request": request,
        "user": user,
    }
    
    # Add CSRF token to context
    context = add_csrf_to_context(request, context)
    
    return templates.TemplateResponse(
        "packages/register.html",
        context,
    )
```

**Manual Method:**
```python
from app.utils.csrf_helpers import get_csrf_token

@router.get("/packages/new")
async def new_package_form(request: Request):
    user = get_current_user(request)
    
    return templates.TemplateResponse(
        "packages/register.html",
        {
            "request": request,
            "user": user,
            "csrf_token": get_csrf_token(request),
        },
    )
```

---

## Common Patterns

### Pattern 1: HTMX Form with Validation

**Template:**
```html
<form hx-post="/packages/{{ package.id }}/status" 
      hx-target="#status-display"
      hx-swap="outerHTML">
    
    <select name="status" required>
        <option value="pending">Pending</option>
        <option value="picked_up">Picked Up</option>
    </select>
    
    <button type="submit">Update Status</button>
</form>
```

**Route:**
```python
@router.post("/packages/{package_id}/status")
async def update_status(
    request: Request,
    package_id: str,
    status: str = Form(...),
):
    # CSRF automatically validated via X-CSRF-Token header
    await package_service.update_status(package_id, status)
    
    return templates.TemplateResponse(
        "components/status_display.html",
        {"request": request, "status": status},
    )
```

### Pattern 2: Multi-Step Form

**Template (Step 1):**
```html
<form method="POST" action="/admin/recipients/import/step2">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    
    <input type="file" name="csv_file" accept=".csv" required>
    <button type="submit">Next</button>
</form>
```

**Route (Step 1):**
```python
@router.post("/admin/recipients/import/step2")
async def import_step2(
    request: Request,
    csv_file: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    
    # Process CSV and show preview
    preview_data = await process_csv(csv_file)
    
    context = {
        "request": request,
        "preview_data": preview_data,
    }
    context = add_csrf_to_context(request, context)
    
    return templates.TemplateResponse("admin/import_preview.html", context)
```

### Pattern 3: API Endpoint with JSON

**JavaScript:**
```javascript
async function deletePackage(packageId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    const response = await fetch(`/api/packages/${packageId}`, {
        method: 'DELETE',
        headers: {
            'X-CSRF-Token': csrfToken,
        },
    });
    
    if (response.ok) {
        showToast('Package deleted successfully', 'success');
    }
}
```

**Route:**
```python
@router.delete("/api/packages/{package_id}")
async def delete_package(
    request: Request,
    package_id: str,
):
    # CSRF automatically validated via X-CSRF-Token header
    await package_service.delete_package(package_id)
    
    return {"success": True}
```

---

## Exempt Routes

Some routes are exempt from CSRF validation:

- `/auth/login` - Special handling in route
- `/health` - Public health check
- `/static/*` - Static files
- `/uploads/*` - Uploaded files
- `/docs`, `/redoc`, `/openapi.json` - API documentation

To add a route to the exempt list, update `app/middleware/csrf.py`:

```python
class CSRFMiddleware(BaseHTTPMiddleware):
    EXEMPT_ROUTES = {
        "/auth/login",
        "/health",
        "/your/new/route",  # Add here
    }
```

---

## Troubleshooting

### Error: "CSRF token validation failed"

**Cause:** CSRF token is missing or invalid.

**Solutions:**

1. **For HTMX requests:**
   - Verify meta tag exists: `<meta name="csrf-token" content="{{ csrf_token }}">`
   - Check HTMX configuration in base.html
   - Inspect network request headers for `X-CSRF-Token`

2. **For form submissions:**
   - Verify hidden input exists: `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`
   - Ensure `csrf_token` is passed to template context
   - Verify route calls `validate_csrf_token(request, csrf_token)`

3. **For JavaScript requests:**
   - Verify token is read from meta tag
   - Check `X-CSRF-Token` header is included
   - Ensure token is not expired (refresh page)

### Token Not Available in Template

**Cause:** CSRF token not passed to template context.

**Solution:**
```python
from app.utils.csrf_helpers import add_csrf_to_context

context = {"request": request, "user": user}
context = add_csrf_to_context(request, context)  # Add this line
```

### HTMX Requests Failing

**Cause:** HTMX configuration not loading or meta tag missing.

**Solution:**
1. Verify base.html includes HTMX configuration script
2. Check browser console for JavaScript errors
3. Inspect network request to verify `X-CSRF-Token` header

---

## Testing CSRF Protection

### Manual Testing

1. **Test with valid token:**
   ```bash
   # Get CSRF token from cookie
   curl -c cookies.txt http://localhost:8000/packages/new
   
   # Extract token and submit form
   curl -b cookies.txt -X POST http://localhost:8000/packages \
     -H "X-CSRF-Token: <token>" \
     -d "tracking_number=PKG123"
   ```

2. **Test without token (should fail):**
   ```bash
   curl -X POST http://localhost:8000/packages \
     -d "tracking_number=PKG123"
   # Expected: 403 Forbidden
   ```

### Automated Testing

```python
def test_csrf_protection(client):
    # Get CSRF token
    response = client.get("/packages/new")
    csrf_token = response.cookies.get("csrf_token")
    
    # Request without token should fail
    response = client.post("/packages", data={"tracking_number": "PKG123"})
    assert response.status_code == 403
    
    # Request with token should succeed
    response = client.post(
        "/packages",
        data={"tracking_number": "PKG123", "csrf_token": csrf_token},
        cookies={"csrf_token": csrf_token},
    )
    assert response.status_code == 200
```

---

## Best Practices

1. **Always use HTMX when possible** - Automatic CSRF handling
2. **Never disable CSRF protection** - Even for "internal" endpoints
3. **Include token in all forms** - Even if using HTMX as fallback
4. **Validate tokens server-side** - Never trust client-side validation
5. **Use helper functions** - `add_csrf_to_context()` for consistency
6. **Test CSRF protection** - Include in integration tests
7. **Monitor failures** - Log and alert on CSRF validation failures

---

## Migration Checklist

When adding CSRF protection to existing routes:

- [ ] Add `csrf_token` to template context
- [ ] Include hidden input in forms: `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`
- [ ] Accept `csrf_token` parameter in route: `csrf_token: str = Form(...)`
- [ ] Validate token in route: `validate_csrf_token(request, csrf_token)`
- [ ] Test form submission works
- [ ] Test HTMX requests work
- [ ] Verify 403 error without token
- [ ] Update integration tests

---

## References

- OWASP CSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- HTMX Security: https://htmx.org/docs/#security

---

## Questions?

If you have questions about CSRF implementation, contact the security team or review:
- `app/middleware/csrf.py` - Middleware implementation
- `app/utils/csrf_helpers.py` - Helper functions
- `docs/SECURITY_FIXES.md` - Detailed security documentation
