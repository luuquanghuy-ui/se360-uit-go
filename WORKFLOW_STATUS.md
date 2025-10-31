# GitHub Actions Workflow Status

## Current Configuration

### ✅ ENABLED Jobs

| Job | Condition | Status |
|-----|-----------|--------|
| **test** | Always run on push/PR | ✅ ACTIVE |

### ❌ DISABLED Jobs

| Job | Condition | Why Disabled |
|-----|-----------|--------------|
| **build-userservice** | `if: ... && false` | ACR không tồn tại |
| **build-tripservice** | `if: ... && false` | ACR không tồn tại |
| **build-driverservice** | `if: ... && false` | ACR không tồn tại |
| **build-locationservice** | `if: ... && false` | ACR không tồn tại |
| **build-paymentservice** | `if: ... && false` | ACR không tồn tại |
| **deploy** | `if: ... && false` | Depends on builds |
| **smoke-test** | `if: ... && false` | Depends on deploy |

---

## Workflow Execution Flow

```
┌──────────────────────────────────────────────┐
│  Push to main/develop                        │
│  OR Pull Request                             │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  ✅ JOB: test                                │
│  - Checkout code                             │
│  - Setup Python 3.11                         │
│  - Install dependencies                      │
│  - Run pytest                                │
│  - Report results                            │
└──────────────────────────────────────────────┘
                    ↓
        ┌───────────────────┐
        │  Test PASSED?     │
        └───────────────────┘
          ↓             ↓
        YES           NO
          ↓             ↓
┌─────────────────┐   ┌──────────────────┐
│ ❌ Builds       │   │ ❌ Workflow      │
│ (SKIPPED due    │   │ FAILED           │
│  to && false)   │   │                  │
└─────────────────┘   └──────────────────┘
          ↓
┌─────────────────┐
│ ❌ Deploy       │
│ (SKIPPED)       │
└─────────────────┘
          ↓
┌─────────────────┐
│ ❌ Smoke test   │
│ (SKIPPED)       │
└─────────────────┘
```

---

## Dependency Chain

```
test
├─► build-userservice ────┐
├─► build-tripservice ────┤
├─► build-driverservice ──┤
├─► build-locationservice ┤
└─► build-paymentservice ─┘
            ↓
         deploy
            ↓
       smoke-test
```

**Key points:**
- `needs: test` → Must wait for test to complete
- All build jobs run **in parallel** (not sequential)
- Deploy only runs after **ALL** builds succeed
- Each job has `if: ... && false` → **DISABLED**

---

## Why Test Runs But Deploy Doesn't

### Test Job
```yaml
test:
  name: Run Tests
  runs-on: ubuntu-latest
  # NO if condition → ALWAYS RUNS
```

### Build/Deploy Jobs
```yaml
build-userservice:
  name: Build UserService
  needs: test
  if: github.ref == 'refs/heads/main' && false  # ← FALSE = SKIP
```

The `&& false` makes the condition **ALWAYS FALSE**, so jobs never run.

---

## How to Enable Full CI/CD

Remove `&& false` from all jobs:

```yaml
# Before
if: github.ref == 'refs/heads/main' && false  # Disabled

# After
if: github.ref == 'refs/heads/main'
```

**But first:** Create ACR or you'll get login errors!

```bash
bash scripts/create-acr.sh
```

---

## Current Behavior

**When you push to main:**
1. ✅ Test runs and passes
2. ❌ Builds skip (disabled)
3. ❌ Deploy skips (disabled)
4. ❌ Smoke tests skip (disabled)

**Result:** Only tests run, nothing deploys.

**This is intentional** because ACR doesn't exist yet!
