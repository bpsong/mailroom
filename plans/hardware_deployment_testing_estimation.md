# Hardware, Deployment, and Testing Estimation

**Date:** 2026-04-06  
**Purpose:** Estimate effort for hardware procurement, environment setup, UAT testing, and production packaging

---

## 1. Hardware Procurement: Development Notebook

### Requirements
- **Purpose:** Dedicated development machine for building and testing mailroom application
- **Minimum Specifications:**
  - CPU: Intel i5 / AMD Ryzen 5 or better
  - RAM: 16GB minimum
  - Storage: 512GB SSD
  - OS: Windows 11 Pro
  - Ports: USB (for barcode scanner testing), HDMI/DisplayPort

### Procurement Effort

| Task | Hours |
|------|-------|
| Research and compare suitable models | 1.0 |
| Obtain quotes and approval process | 1.0 |
| Purchase and delivery coordination | 0.5 |
| Initial unboxing and inventory check | 0.5 |
| **Subtotal** | **3.0** |

### Estimated Cost Range
- **Budget Notebook:** SGD 800 - 1,200
- **Mid-Range Notebook:** SGD 1,200 - 1,800
- **Recommended:** Mid-range for development longevity

---

## 2. Hardware Procurement: UAT Testing Notebook

### Requirements
- **Purpose:** Dedicated UAT machine for actual users to test application
- **Minimum Specifications:**
  - CPU: Intel i3 / AMD Ryzen 3 or better (production-like specs)
  - RAM: 8GB minimum
  - Storage: 256GB SSD
  - OS: Windows 11 Pro
  - Display: 14" or larger (for usability testing)
  - Network: Wi-Fi + Ethernet (for network testing)

### Procurement Effort

| Task | Hours |
|------|-------|
| Research and compare suitable models | 1.0 |
| Obtain quotes and approval process | 1.0 |
| Purchase and delivery coordination | 0.5 |
| Initial unboxing and inventory check | 0.5 |
| **Subtotal** | **3.0** |

### Estimated Cost Range
- **Budget Notebook:** SGD 600 - 900
- **Mid-Range Notebook:** SGD 900 - 1,400
- **Recommended:** Budget-to-mid-range (production-like environment)

---

## 3. Development Notebook Setup

### Setup Procedure

| Task | Hours |
|------|-------|
| Windows 11 initial setup and updates | 1.0 |
| Install Python 3.13 and verify | 0.5 |
| Install Git and configure | 0.5 |
| Install VS Code and extensions | 0.5 |
| Install project dependencies (pyproject.toml) | 0.5 |
| Clone repository and verify build | 0.5 |
| Install DuckDB and verify database | 0.5 |
| Configure environment variables (.env) | 0.5 |
| Install Node.js (for Tailwind/Playwright) | 0.5 |
| Install Playwright browsers | 0.5 |
| Run existing test suite to verify setup | 0.5 |
| Configure Caddy (if using for local dev) | 0.5 |
| **Subtotal** | **7.0** |

### Setup Verification Checklist
- [ ] `python -m pytest tests/` passes
- [ ] `python -m app.main` starts successfully
- [ ] Local app accessible at http://127.0.0.1:8000
- [ ] Playwright smoke test passes
- [ ] Database migrations run successfully

---

## 4. UAT Notebook Setup

### Setup Procedure

| Task | Hours |
|------|-------|
| Windows 11 initial setup and updates | 1.0 |
| Install Python 3.13 (runtime only) | 0.5 |
| Install Caddy as reverse proxy | 1.0 |
| Deploy application code from repository | 0.5 |
| Configure production-like .env | 0.5 |
| Set up Windows Service for auto-start | 1.0 |
| Configure firewall rules for network access | 0.5 |
| Install and configure SMTP relay (if needed) | 1.0 |
| Create test user accounts | 0.5 |
| Seed test data (recipients, packages) | 0.5 |
| Verify network accessibility from other devices | 0.5 |
| **Subtotal** | **8.0** |

### UAT Setup Verification Checklist
- [ ] App accessible via network URL
- [ ] Test users can log in
- [ ] All roles (operator, admin, super_admin) functional
- [ ] Email notifications configured (or mocked)
- [ ] Barcode scanner tested (if available)

---

## 5. Code Push Procedure: Dev to UAT

### Deployment Workflow

| Task | Hours |
|------|-------|
| Create deployment script (PowerShell) | 2.0 |
| Configure Git-based deployment | 1.0 |
| Set up environment-specific configuration | 1.0 |
| Create rollback procedure documentation | 1.0 |
| Test deployment end-to-end | 1.5 |
| Document deployment runbook | 1.0 |
| **Subtotal** | **7.5** |

### Deployment Steps (Runbook Outline)
1. Commit and push code to `uat` branch from dev machine
2. On UAT machine: `git pull origin uat`
3. Run database migrations: `python scripts/migrate.py`
4. Restart application service
5. Verify health endpoint: `curl http://<uat-ip>:8000/health`
6. Smoke test login and core functionality

---

## 6. Manual UAT Testing (2 Users)

### Test Scope
- **Duration:** Estimated 2 testing sessions per user
- **Users:** 1 Operator + 1 Admin (or 2 Operators)
- **Test Areas:** Core workflows, new features, edge cases

### Test Plan

| Test Area | Tasks | Hours per User | Total Hours |
|-----------|-------|----------------|-------------|
| Authentication & Navigation | Login, logout, password change, profile | 1.0 | 2.0 |
| Package Registration | Inbound registration, barcode scan, photo upload | 2.0 | 4.0 |
| Package Management | Status updates, search, detail view | 1.5 | 3.0 |
| Outbound Tracking | Outbound registration, status flow | 1.5 | 3.0 |
| Email Notifications | Trigger notifications, verify delivery | 1.0 | 2.0 |
| Signature Capture | Sign for package, verify storage | 1.0 | 2.0 |
| Proof of Delivery | Generate POD, verify content | 1.0 | 2.0 |
| Reports & Export | CSV export, monthly report generation | 1.0 | 2.0 |
| Admin Functions | User management, recipient management, settings | 1.5 | 3.0 |
| Edge Cases & Error Handling | Invalid inputs, duplicate scans, network issues | 1.5 | 3.0 |
| **Subtotal per User** | | **13.0** | **26.0** |

### UAT Feedback Collection

| Task | Hours |
|------|-------|
| Prepare test scripts and feedback forms | 1.0 |
| Conduct UAT session coordination | 1.0 |
| Collect and consolidate feedback | 2.0 |
| Prioritize bugs and improvements | 1.0 |
| **Subtotal** | **5.0** |

### Total UAT Testing Effort: **31.0 hours**

---

## 7. Production EXE Binary Packaging

### Approach
Package the FastAPI application as a single Windows executable using PyInstaller for easy deployment to production site.

### Effort Breakdown

| Task | Hours |
|------|-------|
| Research PyInstaller configuration for FastAPI | 1.5 |
| Create PyInstaller spec file | 1.0 |
| Configure hidden imports and data files | 1.5 |
| Handle DuckDB binary bundling | 1.5 |
| Handle templates and static files bundling | 1.5 |
| Create build script (PowerShell) | 1.0 |
| Test EXE execution locally | 1.5 |
| Resolve bundling issues (templates, static, DB) | 2.5 |
| Optimize EXE size and startup time | 1.0 |
| Create production deployment guide | 1.5 |
| Test deployment on clean Windows machine | 2.0 |
| **Subtotal** | **16.5** |

### Technical Considerations
- **Templates/Static Files:** Must be bundled as data files or embedded
- **DuckDB Database:** Either bundled or created on first run
- **Configuration:** External .env file for production flexibility
- **Service Mode:** Consider Windows Service wrapper for auto-start
- **Logging:** File-based logging for production troubleshooting

### PyInstaller Spec File Requirements
```python
# Key configurations needed
hiddenimports=['app', 'app.main', 'duckdb', 'fastapi', 'uvicorn']
datas=[('templates/', 'templates/'), ('static/', 'static/')]
```

---

## Summary: All Effort Estimates

| Phase | Task | Hours |
|-------|------|-------|
| **Hardware** | Dev Notebook Procurement | 3.0 |
| **Hardware** | UAT Notebook Procurement | 3.0 |
| **Setup** | Dev Notebook Setup | 7.0 |
| **Setup** | UAT Notebook Setup | 8.0 |
| **Deployment** | Code Push Procedure Setup | 7.5 |
| **Testing** | Manual UAT Testing (2 users) | 31.0 |
| **Production** | EXE Binary Packaging | 16.5 |
| | **SUBTOTAL** | **76.0** |

---

## Combined Total: Feature Development + Infrastructure

| Category | Hours |
|----------|-------|
| Feature Development (from feature_improvements_estimation.md) | 58.5 |
| Hardware, Deployment, Testing, Production Packaging | 76.0 |
| **GRAND SUBTOTAL** | **134.5** |

---

## Contingency Buffer (15%)

| Category | Hours |
|----------|-------|
| Grand Subtotal | 134.5 |
| 15% Buffer | 20.2 |
| **GRAND TOTAL** | **154.7** |

**Rounded Grand Total: ~155 hours**

---

## Recommended Timeline

| Phase | Duration | Cumulative Hours |
|-------|----------|------------------|
| Week 1-2: Hardware + Dev Setup | 2 weeks | 21.0 |
| Week 2-4: Feature Development Phase 1 | 2 weeks | 39.5 |
| Week 4-6: Feature Development Phase 2 | 2 weeks | 62.0 |
| Week 6-7: Feature Development Phase 3 | 1.5 weeks | 79.5 |
| Week 7-8: UAT Setup + Deployment Pipeline | 1.5 weeks | 95.0 |
| Week 8-10: UAT Testing (2 users) | 2 weeks | 126.0 |
| Week 10-11: Production EXE Packaging | 1.5 weeks | 142.5 |
| Week 11-12: Buffer for unforeseen tasks | 1.5 weeks | 155.0 |

**Estimated Project Duration: 12 weeks (~3 months)**

---

## Hardware Budget Estimate

| Item | Low Estimate (SGD) | High Estimate (SGD) |
|------|-------------------|---------------------|
| Development Notebook | 1,200 | 1,800 |
| UAT Testing Notebook | 600 | 1,400 |
| **Total Hardware** | **1,800** | **3,200** |

---

## Assumptions

1. Hardware procurement process is straightforward (no complex approval delays)
2. Network infrastructure exists for UAT machine accessibility
3. SMTP server credentials available for email notification testing
4. Production site has Windows machine capable of running the EXE
5. Users are available for UAT within the planned timeline
6. No major architectural changes required beyond estimated scope
7. PyInstaller can successfully bundle all dependencies (DuckDB compatibility confirmed)

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hardware delivery delays | Schedule slip | Order early; have backup machines available |
| UAT user availability | Testing delays | Schedule sessions in advance; prepare async test scripts |
| PyInstaller bundling issues | Production deployment complexity | Test early; consider alternative packaging (zip + Python runtime) |
| DuckDB file locking in production | Runtime errors | Test concurrent access patterns; consider write queue |
| SMTP configuration complexity | Email feature delays | Use mock SMTP initially; integrate real SMTP in UAT |
