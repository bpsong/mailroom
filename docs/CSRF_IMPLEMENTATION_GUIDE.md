# CSRF Implementation Guide for Developers

This guide describes how CSRF protection works in the current Mailroom codebase and how to implement new endpoints safely.

## Current Implementation

Source: `app/middleware/csrf.py`

### Protected methods
- `POST`
- `PUT`
- `PATCH`
- `DELETE`

### Exempt routes
- Exact: `/health`
- Prefixes: `/static/`, `/uploads/`, `/docs`, `/redoc`, `/openapi.json`

### Validation model
- Cookie `csrf_token` is required.
- If `X-CSRF-Token` header is present, middleware validates it directly.
- For standard form submits, routes must call `validate_csrf_token(request, csrf_token)`.

## Template Requirements

`templates/base.html` already provides:
- `<meta name="csrf-token" content="{{ csrf_token_value() }}">`
- HTMX request hook that injects `X-CSRF-Token`
- form token helper usage support (`{{ csrf_input()|safe }}`)

For non-HTMX forms, include hidden field:
```html
<form method="POST" action="/admin/users/new">
  {{ csrf_input()|safe }}
  <!-- fields -->
</form>
```

## Route Patterns

## Pattern 1: HTMX/AJAX Header-based CSRF

Use when submitting via HTMX/fetch and header is automatically sent.

```python
@router.post("/packages/{package_id}/status")
@require_auth
async def update_package_status(
    request: Request,
    package_id: str,
    status: str = Form(...),
    notes: str | None = Form(None),
    csrf_token: str = Form(...),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

    # business logic...
```

Notes:
- Existing routes often validate both form token and middleware state; keep that pattern for consistency.

## Pattern 2: Standard Form Submission

```python
@router.post("/admin/users/new")
@require_role("admin")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    csrf_token: str = Form(...),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

    # business logic...
```

## Pattern 3: File Upload Forms

```python
@router.post("/admin/recipients/import/validate")
@require_role("admin")
async def validate_import(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
):
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token validation failed")

    # validation logic...
```

## Current Multi-Step Import Endpoints

The current import flow uses:
- `POST /admin/recipients/import/validate`
- `POST /admin/recipients/import/confirm`

Do not use legacy `/step2` examples.

## Troubleshooting

### 403 CSRF validation failed
Check:
1. `csrf_token` cookie is present.
2. Form includes hidden `csrf_token` (or header is present).
3. Route accepts `csrf_token: str = Form(...)`.
4. Route calls `validate_csrf_token(request, csrf_token)`.

### HTMX request fails unexpectedly
Check:
1. Base template is used (contains HTMX CSRF hook).
2. `meta[name="csrf-token"]` is present in DOM.
3. Request includes `X-CSRF-Token` header in browser dev tools.

## Minimal Checklist for New State-Changing Endpoint

- [ ] Add `csrf_token: str = Form(...)` for form handlers.
- [ ] Call `validate_csrf_token(request, csrf_token)`.
- [ ] Ensure template uses `{{ csrf_input()|safe }}`.
- [ ] Verify request returns `403` when token is missing/invalid.
- [ ] Verify valid token request succeeds.

## References

- Middleware: `app/middleware/csrf.py`
- Base template helpers: `templates/base.html`
- Existing route examples: `app/routes/packages.py`, `app/routes/admin.py`, `app/routes/user.py`, `app/routes/auth.py`
