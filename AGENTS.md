# Workspace Agent Notes

## Environment

- Workspace root: [`d:/python_code/mailroom`](AGENTS.md)
- Operating system: Windows
- Default shell in this workspace is commonly [`cmd.exe`](AGENTS.md), but PowerShell is preferred for reliable test execution.

## Python and Pytest Execution

- Prefer explicit interpreter invocation instead of bare `pytest`.
- Recommended command pattern:
  - `C:\Python313\python.exe -m pytest tests\unit\test_config_settings.py -v`
- Do not rely on bare `pytest`, because interpreter resolution may differ from `python` on this machine.

## Known Windows PATH Issue

- This workspace has experienced pytest hangs/crashes caused by shell `PATH` contamination.
- The main issue is Git Unix tooling in `d:\Program Files\Git\usr\bin` interfering with Python/pytest runtime behavior.
- Symptom observed: pytest appears to hang or crashes before normal output.

## Recommended Test Shell Setup

Use PowerShell and reset `PATH` before running pytest:

```powershell
$env:PATH='C:\Python313;C:\Python313\Scripts;C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem'
$env:SECRET_KEY='test-secret-key'
$env:APP_ENV='testing'
C:\Python313\python.exe -m pytest tests\unit\test_config_settings.py tests\unit\test_auth_service.py tests\test_security_fixes.py -v
```

## Notes for Future Agents

- If pytest hangs, suspect environment/toolchain issues before suspecting application code such as [`app/config.py`](app/config.py) or [`tests/conftest.py`](tests/conftest.py).
- A virtual environment is optional for this workspace, not mandatory, as long as PowerShell uses a clean `PATH` and pytest is invoked via explicit Python.
- Pydantic deprecation warnings currently appear from model files and are unrelated to the pytest environment issue.
