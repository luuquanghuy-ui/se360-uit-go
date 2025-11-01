# Kế hoạch Module C: Thiết kế cho Security (DevSecOps)

Dựa trên phân tích kiến trúc hiện tại của UIT-Go, tôi đã xây dựng kế hoạch chi tiết cho Module C - Security Engineering với triết lý Zero Trust.

## 📊 Tổng quan hiện trạng

**Hệ thống hiện tại:**
- Kiến trúc microservices trên Azure AKS
- 5 services: UserService, TripService, DriverService, LocationService, PaymentService
- Databases: PostgreSQL, CosmosDB (MongoDB API), Redis
- CI/CD: GitHub Actions → ACR → AKS
- Network: VNet 172.16.0.0/16, AKS subnet 172.16.1.0/24

## 🎯 Kế hoạch chi tiết theo nhiệm vụ

### **1. Mô hình hóa Mối đe dọa (Threat Modeling)**

#### **1.1 Xây dựng Data Flow Diagram (DFD)**

**Mục tiêu:** Vẽ sơ đồ luồng dữ liệu chi tiết với các thành phần:
- External Entities: Passenger App, Driver App, VNPay, Mapbox
- Processes: UserService, TripService, DriverService, LocationService, PaymentService
- Data Stores: PostgreSQL, CosmosDB, Redis
- Data Flows: HTTP REST, WebSocket, Database connections

**Công cụ:** Draw.io, Lucidchart hoặc Microsoft Threat Modeling Tool

**Deliverables:**
- DFD Level 0 (Context Diagram) - Tổng quan hệ thống
- DFD Level 1 - Chi tiết từng service
- DFD Level 2 - Chi tiết flows quan trọng (Authentication, Payment, Real-time tracking)

#### **1.2 STRIDE Analysis**

Phân tích từng component theo mô hình STRIDE:

| Threat Category | Attack Surface | Potential Threats | Mitigation |
|----------------|----------------|-------------------|------------|
| **S**poofing | JWT Authentication | Token stealing, replay attacks | Implement short-lived tokens, refresh mechanism, token rotation |
| | Service-to-Service Auth | Malicious service impersonation | Add audience (`aud`) claim, mutual TLS |
| **T**ampering | API Requests | Man-in-the-middle, payload modification | Enforce HTTPS/TLS everywhere, request signing |
| | Database | SQL injection, NoSQL injection | Parameterized queries, input validation |
| **R**epudiation | Payment transactions | User denies payment | Comprehensive audit logs, transaction IDs |
| | Trip history | Driver/passenger disputes | Immutable event logs, blockchain consideration |
| **I**nformation Disclosure | Secrets in K8s | Exposed credentials | Use Azure Key Vault, encrypt secrets at rest |
| | Database connections | Connection string leaks | VNet integration, private endpoints |
| | Logs | Sensitive data in logs | PII scrubbing, structured logging |
| **D**enial of Service | Public endpoints | API flooding | Rate limiting, WAF, DDoS protection |
| | WebSocket | Connection exhaustion | Connection limits, timeouts |
| **E**levation of Privilege | RBAC bypass | Unauthorized admin access | Principle of least privilege, RBAC audit |
| | Service tokens | Cross-service unauthorized calls | Scope-based access control |

**Deliverables:**
- STRIDE analysis matrix
- Risk assessment (High/Medium/Low priority)
- Mitigation roadmap với timeline

---

### **2. Thiết kế Kiến trúc Mạng Zero Trust**

#### **2.1 Network Segmentation (Azure VNet)**

```
VNet: 172.16.0.0/16
├─ AKS Subnet: 172.16.1.0/24 (hiện tại)
├─ PostgreSQL Subnet: 172.16.2.0/24 (đã có)
├─ CosmosDB Private Endpoint Subnet: 172.16.3.0/24 (MỚI)
├─ Redis Subnet: 172.16.4.0/24 (MỚI)
├─ Management Subnet: 172.16.5.0/24 (Bastion/Jump box)
└─ Application Gateway Subnet: 172.16.6.0/24 (WAF)
```

#### **2.2 Network Security Groups (NSGs)**

**NSG cho AKS Subnet (172.16.1.0/24):**
```hcl
# Inbound Rules
- Allow: Application Gateway subnet → AKS (443, 80)
- Allow: AKS nodes → Azure services (HTTPS)
- Deny: Internet → AKS nodes (ALL)

# Outbound Rules
- Allow: AKS → Database subnets (5432 PostgreSQL, 6379 Redis, 10255 CosmosDB)
- Allow: AKS → Internet (443 for external APIs: Mapbox, VNPay)
- Deny: All other traffic
```

**NSG cho Database Subnets:**
```hcl
# Inbound Rules
- Allow: AKS subnet → PostgreSQL (5432)
- Allow: AKS subnet → Redis (6379)
- Allow: AKS subnet → CosmosDB (10255)
- Deny: All other traffic

# Outbound Rules
- Deny: All (databases should not initiate outbound)
```

#### **2.3 Azure Private Endpoints**

Cấu hình Private Link cho:
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Azure Cosmos DB

**Lợi ích:**
- Traffic không đi qua Internet
- Sử dụng private IP trong VNet
- Giảm attack surface

#### **2.4 ModSecurity WAF (Web Application Firewall)**

**Tại sao cần WAF cho UIT-Go?**

| Vấn đề hiện tại | Giải pháp ModSecurity WAF |
|----------------|---------------------------|
| API endpoints exposed trực tiếp qua Ingress | WAF làm protection layer đầu tiên |
| Không có defense chống OWASP Top 10 | OWASP CRS (Core Rule Set) tự động block attacks |
| Payment API dễ bị tấn công (SQL injection, XSS) | ModSecurity rules cho financial services |
| Không có rate limiting tập trung | ModSecurity rate limiting module |
| WebSocket flooding risk | Connection rate limiting |
| Bot attacks, credential stuffing | Bot detection rules |

**Tại sao chọn ModSecurity thay vì Azure Application Gateway WAF?**

| Criteria | ModSecurity | Azure App Gateway WAF |
|----------|-------------|----------------------|
| **Cost** | **FREE** (open-source) | ~$275-455/month |
| **Flexibility** | Fully customizable rules | Limited customization |
| **OWASP CRS** | Latest version (4.x) | Version 3.2 (older) |
| **Learning curve** | Steep (manual config) | Easy (managed service) |
| **Integration** | Native với NGINX Ingress | Separate Azure resource |
| **Control** | Full control | Managed by Azure |
| **Best for** | Cost-sensitive, hands-on teams | Enterprise, managed services |

**Quyết định:** Sử dụng **ModSecurity** vì:
- ✅ Zero cost (quan trọng cho startup/student project)
- ✅ Tích hợp trực tiếp với NGINX Ingress Controller
- ✅ Full control và customization
- ✅ Community support mạnh (OWASP CRS)

**Kiến trúc ModSecurity WAF với Ingress API Gateway:**
```
Internet (Client Apps)
   │
   ▼
Azure Load Balancer (Public IP)
   │
   ▼
NGINX Ingress Controller (API Gateway) + ModSecurity WAF
   │ - ModSecurity v3 (libmodsecurity)
   │ - OWASP CRS 4.0 (Core Rule Set)
   │ - Custom rules cho UIT-Go
   │ - Type: LoadBalancer
   │
   │ Path-based Routing:
   ├─ /api/users/*     → UserService (ClusterIP)
   ├─ /api/trips/*     → TripService (ClusterIP)
   ├─ /api/drivers/*   → DriverService (ClusterIP)
   ├─ /api/locations/* → LocationService (ClusterIP)
   ├─ /api/payments/*  → PaymentService (ClusterIP)
   └─ /ws              → LocationService WebSocket (ClusterIP)
```

**Lợi ích của kiến trúc này:**
- ✅ WAF inspect TẤT CẢ traffic trước khi đến services
- ✅ Không có single point of failure (UserService không còn là reverse proxy)
- ✅ Ingress làm API Gateway: routing, SSL, CORS, rate limiting
- ✅ ModSecurity bảo vệ toàn bộ surface area
- ✅ Tất cả services đều ClusterIP (không exposed ra ngoài)

**ModSecurity Configuration Chi tiết:**

1. **OWASP Core Rule Set (CRS) 4.0:**
   - **REQUEST-911-METHOD-ENFORCEMENT:** HTTP method validation
   - **REQUEST-920-PROTOCOL-ENFORCEMENT:** HTTP protocol compliance
   - **REQUEST-921-PROTOCOL-ATTACK:** Protocol attack detection
   - **REQUEST-930-APPLICATION-ATTACK-LFI:** Local File Inclusion
   - **REQUEST-931-APPLICATION-ATTACK-RFI:** Remote File Inclusion
   - **REQUEST-932-APPLICATION-ATTACK-RCE:** Remote Code Execution
   - **REQUEST-933-APPLICATION-ATTACK-PHP:** PHP Injection
   - **REQUEST-941-APPLICATION-ATTACK-XSS:** Cross-Site Scripting
   - **REQUEST-942-APPLICATION-ATTACK-SQLI:** SQL Injection
   - **REQUEST-943-APPLICATION-ATTACK-SESSION-FIXATION:** Session attacks
   - **REQUEST-949-BLOCKING-EVALUATION:** Final blocking decision

2. **ModSecurity Modes:**
   - **DetectionOnly:** Log attacks but don't block (testing phase)
   - **On:** Active blocking mode (production)

   Recommend: Start với DetectionOnly trong 1-2 tuần để tune rules

3. **Custom Rules cho UIT-Go:**

```nginx
# Rate Limiting Rule (100 requests/min per IP)
SecAction "id:900100,phase:1,nolog,pass,initcol:ip=%{REMOTE_ADDR}"
SecRule IP:REQUEST_RATE "@gt 100" \
    "id:900101,phase:1,deny,status:429,\
    msg:'Rate limit exceeded (100 req/min)',\
    setvar:ip.request_rate=+1"

# Geo-blocking (Block high-risk countries)
SecRule REMOTE_ADDR "@geoLookup" \
    "id:900102,phase:1,chain,deny,msg:'Access denied from blocked country'"
SecRule GEO:COUNTRY_CODE "@rx ^(KP|IR)$"

# Block malicious User-Agents
SecRule REQUEST_HEADERS:User-Agent "@rx (sqlmap|nikto|nmap|masscan|metasploit)" \
    "id:900103,phase:1,deny,status:403,\
    msg:'Malicious scanner detected'"

# Payment API Protection (strict amount validation)
SecRule REQUEST_URI "@beginsWith /api/payment" \
    "id:900104,phase:2,chain,deny,status:400,\
    msg:'Invalid payment amount format'"
SecRule ARGS:amount "!@rx ^[0-9]{1,10}$"

# Authentication API Rate Limiting (5 login attempts per minute)
SecAction "id:900105,phase:1,nolog,pass,\
    initcol:ip=%{REMOTE_ADDR},\
    initcol:ip=%{REQUEST_URI}"
SecRule REQUEST_URI "@beginsWith /auth/login" \
    "id:900106,phase:1,chain,deny,status:429,\
    msg:'Login rate limit exceeded (5/min)'"
SecRule IP:LOGIN_RATE "@gt 5" \
    "setvar:ip.login_rate=+1"

# Block suspicious file extensions
SecRule REQUEST_FILENAME "@rx \.(bak|sql|zip|tar|gz|log|old)$" \
    "id:900107,phase:1,deny,status:403,\
    msg:'Suspicious file extension blocked'"
```

4. **Logging & Monitoring:**

```nginx
# ModSecurity Audit Log Configuration
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogParts ABIJDEFHZ
SecAuditLogType Serial
SecAuditLog /var/log/modsec_audit.log

# Send logs to Azure Log Analytics
# Via FluentBit/Fluent-d sidecar container
```

**Triển khai ModSecurity trên NGINX Ingress:**

**Option 1: NGINX Ingress Controller với ModSecurity built-in**

```yaml
# k8s/nginx-ingress-modsecurity.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-modsecurity
  namespace: ingress-nginx
data:
  enable-modsecurity: "true"
  enable-owasp-modsecurity-crs: "true"
  modsecurity-snippet: |
    # OWASP CRS 4.0
    Include /etc/nginx/owasp-modsecurity-crs/crs-setup.conf
    Include /etc/nginx/owasp-modsecurity-crs/rules/*.conf

    # Custom UIT-Go rules
    SecRuleEngine On
    SecRequestBodyAccess On
    SecRule REQUEST_HEADERS:Content-Type "text/xml" \
         "id:'200000',phase:1,t:none,t:lowercase,pass,nolog,ctl:requestBodyProcessor=XML"

    # Rate limiting
    SecAction "id:900100,phase:1,nolog,pass,initcol:ip=%{REMOTE_ADDR}"
    SecRule IP:REQUEST_RATE "@gt 100" \
        "id:900101,phase:1,deny,status:429,\
        msg:'Rate limit exceeded',\
        setvar:ip.request_rate=+1"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-ingress-controller
  namespace: ingress-nginx
spec:
  template:
    spec:
      containers:
      - name: nginx-ingress-controller
        image: k8s.gcr.io/ingress-nginx/controller:v1.8.0
        args:
          - /nginx-ingress-controller
          - --configmap=$(POD_NAMESPACE)/nginx-ingress-modsecurity
        volumeMounts:
        - name: modsecurity-rules
          mountPath: /etc/nginx/owasp-modsecurity-crs
      volumes:
      - name: modsecurity-rules
        configMap:
          name: owasp-crs-configmap
```

**Option 2: Separate ModSecurity Container (Sidecar Pattern)**

```yaml
# k8s/modsecurity-sidecar.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-with-modsecurity
spec:
  template:
    spec:
      containers:
      # Main NGINX container
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80

      # ModSecurity sidecar
      - name: modsecurity
        image: owasp/modsecurity-crs:nginx-alpine
        ports:
        - containerPort: 8080
        env:
        - name: PARANOIA
          value: "2"  # OWASP CRS Paranoia Level (1-4)
        - name: ANOMALY_INBOUND
          value: "5"  # Blocking threshold
        - name: ANOMALY_OUTBOUND
          value: "4"
        volumeMounts:
        - name: modsecurity-custom-rules
          mountPath: /etc/modsecurity.d/custom-rules

      volumes:
      - name: modsecurity-custom-rules
        configMap:
          name: modsecurity-custom-rules
```

**OWASP CRS Paranoia Levels:**

| Level | Description | False Positives | Security |
|-------|-------------|-----------------|----------|
| PL1 | Basic protection | Low | Medium |
| PL2 | Recommended (default) | Medium | High |
| PL3 | Aggressive | High | Very High |
| PL4 | Maximum protection | Very High | Maximum |

**Recommend:** Start với **Paranoia Level 2**, tune rules dựa trên false positives

**Performance Tuning:**

```nginx
# Optimize ModSecurity performance
SecRuleEngine On
SecRequestBodyLimit 13107200  # 12.5 MB
SecRequestBodyNoFilesLimit 131072  # 128 KB
SecRequestBodyInMemoryLimit 131072
SecResponseBodyLimit 524288  # 512 KB
SecResponseBodyLimitAction ProcessPartial

# Skip rules cho static files
SecRule REQUEST_URI "@beginsWith /static" \
    "id:900200,phase:1,pass,nolog,ctl:ruleEngine=Off"
```

**Testing & Validation:**

```bash
# Test SQL Injection blocking
curl -X POST "http://your-domain.com/api/users?id=1' OR '1'='1"
# Expected: 403 Forbidden (blocked by rule 942100)

# Test XSS blocking
curl -X POST "http://your-domain.com/api/search?q=<script>alert('XSS')</script>"
# Expected: 403 Forbidden (blocked by rule 941100)

# Test rate limiting
for i in {1..150}; do curl http://your-domain.com/; done
# Expected: HTTP 429 after request 101

# View ModSecurity logs
kubectl logs -n ingress-nginx deployment/nginx-ingress-controller | grep ModSecurity
```

**Cost Analysis:**

| Component | Cost |
|-----------|------|
| ModSecurity | **$0** (open-source) |
| NGINX Ingress Controller | **$0** (already deployed) |
| OWASP CRS | **$0** (open-source) |
| Compute overhead | ~5-10% CPU/Memory increase |
| **Total** | **$0** (chỉ có overhead nhỏ) |

**ROI Justification:**
- ✅ Zero licensing cost
- ✅ Industry-standard protection (OWASP CRS)
- ✅ Full control và customization
- ✅ Same protection level as commercial WAF
- ✅ Learning opportunity cho team

**Deliverables:**
- [ ] NGINX Ingress ConfigMap với ModSecurity enabled
- [ ] OWASP CRS 4.0 deployment
- [ ] Custom rules cho UIT-Go (payment, auth, rate limiting)
- [ ] Logging configuration → Azure Log Analytics
- [ ] Testing script để validate WAF rules
- [ ] Runbook: "How to analyze ModSecurity logs"
- [ ] Runbook: "How to add/tune ModSecurity rules"
- [ ] Runbook: "How to handle false positives"

---

### **3. Tích hợp Security vào CI/CD Pipeline (Shift-left Security)**

#### **3.1 Static Application Security Testing (SAST)**

**Tools:** Bandit (Python), SonarQube, Semgrep

**Integration vị trí:** Sau bước "Checkout code", trước "Build"

```yaml
# .github/workflows/deploy.yml
sast:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Run Bandit SAST
      run: |
        pip install bandit
        bandit -r UserService/ TripService/ DriverService/ LocationService/ PaymentService/ -f json -o bandit-report.json
    - name: Upload SAST results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: bandit-report.json
```

#### **3.2 Dependency Vulnerability Scanning**

**Tools:** Safety, Trivy, Snyk

```yaml
dependency-check:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Check Python dependencies
      run: |
        pip install safety
        safety check -r UserService/requirements.txt --json
```

#### **3.3 Container Image Scanning**

**Tools:** Trivy, Microsoft Defender for Containers

```yaml
# Thêm vào job 'build', sau khi build image
- name: Scan Docker image (Trivy)
  run: |
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
      aquasec/trivy image --severity HIGH,CRITICAL \
      ${{ env.ACR_NAME }}.azurecr.io/userservice:${{ github.sha }}
```

#### **3.4 Secrets Scanning**

**Tools:** TruffleHog, GitGuardian, GitHub Secret Scanning

```yaml
secrets-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0
    - name: TruffleHog scan
      run: |
        docker run --rm -v "$PWD:/pwd" trufflesecurity/trufflehog:latest \
          filesystem /pwd --json
```

#### **3.5 Infrastructure as Code (IaC) Scanning**

**Tools:** Checkov, tfsec, Terraform Sentinel

```yaml
iac-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Scan Terraform files
      run: |
        pip install checkov
        checkov -d terraform/ --framework terraform
```

#### **3.6 Dynamic Application Security Testing (DAST)**

**Tools:** OWASP ZAP

```yaml
# Chạy sau smoke_test
dast:
  runs-on: ubuntu-latest
  needs: smoke_test
  steps:
    - name: Run OWASP ZAP scan
      run: |
        docker run --rm -v $(pwd):/zap/wrk/:rw \
          owasp/zap2docker-stable zap-baseline.py \
          -t ${{ steps.lb-ip.outputs.API_URL }} -r zap-report.html
```

**Deliverables:**
- Updated GitHub Actions workflow với 6 security gates
- CI/CD pipeline diagram với security checkpoints
- Security policy: fail build nếu tìm thấy HIGH/CRITICAL vulnerabilities

---

### **4. Defense-in-Depth Layers**

#### **Layer 1: Perimeter Security**
- **Azure DDoS Protection Standard:** Chống DDoS attacks
- **Application Gateway WAF:** OWASP Top 10 protection
- **Azure Front Door:** Global load balancing với built-in DDoS

#### **Layer 2: Network Security**
- **NSGs:** Micro-segmentation theo subnets
- **Azure Firewall:** Centralized egress control
- **Private Endpoints:** Loại bỏ public exposure cho databases

#### **Layer 3: Identity & Access**
- **Azure AD Integration:** Centralized identity provider
- **RBAC cho AKS:** Role-based access control cho K8s resources
- **Managed Identities:** Service authentication không cần credentials
- **JWT với short expiry:** Access token 30 min, refresh token 7 days

#### **Layer 4: Application Security**
- **Input validation:** Pydantic models với strict validation
- **Output encoding:** Prevent XSS
- **Parameterized queries:** Prevent SQL/NoSQL injection
- **Rate limiting:** Per-user, per-IP throttling

#### **Layer 5: Data Security**
- **Encryption at rest:**
  - PostgreSQL: Azure-managed TDE
  - CosmosDB: Automatic encryption
  - Redis: RDB encryption
- **Encryption in transit:** TLS 1.3 everywhere
- **Secrets Management:** Azure Key Vault integration

#### **Layer 6: Logging & Monitoring**
- **Azure Monitor:** Centralized logging (đã có)
- **Log Analytics:** Query và alerting
- **Azure Sentinel (SIEM):** Threat detection với ML
- **Audit logs:** Immutable logs cho compliance

#### **Layer 7: Incident Response**
- **Security playbooks:** Automated response với Azure Logic Apps
- **Backup & DR:** Point-in-time restore cho databases
- **Rollback mechanism:** Kubernetes rollout undo

**Deliverables:**
- Defense-in-depth architecture diagram
- Terraform/K8s manifests cho từng layer
- Security controls matrix (NIST CSF mapping)

---

### **5. Triển khai cụ thể**

#### **Phase 1: Foundation (Week 1-2)**
- [ ] Complete Threat Model (DFD + STRIDE)
- [ ] Design network architecture với Zero Trust principles
- [ ] Set up Azure Key Vault
- [ ] Implement Private Endpoints cho databases

#### **Phase 2: CI/CD Security (Week 3)**
- [ ] Integrate SAST (Bandit)
- [ ] Integrate dependency scanning (Safety, Trivy)
- [ ] Integrate container scanning (Trivy)
- [ ] Integrate secrets scanning (TruffleHog)
- [ ] Integrate IaC scanning (Checkov)

#### **Phase 3: Network Security (Week 4)**
- [ ] Deploy Azure Application Gateway với WAF
- [ ] Configure NSGs cho tất cả subnets
- [ ] Implement Azure Firewall cho egress control
- [ ] Set up DDoS Protection Standard

#### **Phase 4: Application Hardening (Week 5)**
- [ ] Implement rate limiting middleware
- [ ] Add request signing cho service-to-service
- [ ] Implement comprehensive input validation
- [ ] Add audit logging cho sensitive operations

#### **Phase 5: Monitoring & Response (Week 6)**
- [ ] Configure Azure Sentinel
- [ ] Set up security alerts và playbooks
- [ ] Create incident response runbooks
- [ ] Conduct security testing (penetration test)

#### **Phase 6: Documentation & Training (Week 7)**
- [ ] Write ADRs cho security decisions
- [ ] Create security runbooks
- [ ] Document threat model findings
- [ ] Team training session

---

### **6. Architectural Decision Records (ADRs) cần viết**

1. **ADR-006: Zero Trust Network Architecture**
   - Context: Traditional perimeter security insufficient
   - Decision: Implement Zero Trust với micro-segmentation
   - Consequences: Higher complexity, better security posture

2. **ADR-007: Azure Key Vault for Secrets Management**
   - Context: Secrets hiện tại lưu trong K8s Secrets (base64 encoded)
   - Decision: Migrate sang Azure Key Vault với CSI driver
   - Consequences: Centralized secret rotation, audit trail

3. **ADR-008: Service Mesh for mTLS**
   - Context: Service-to-service communication chưa encrypted
   - Decision: Evaluate Istio/Linkerd cho mutual TLS
   - Consequences: Encrypted internal traffic, complexity tăng

4. **ADR-009: WAF vs API Gateway**
   - Context: Cần protection layer trước AKS
   - Decision: Azure Application Gateway WAF
   - Consequences: OWASP protection, Azure-native integration

5. **ADR-010: Shift-Left Security in CI/CD**
   - Context: Security testing hiện tại minimal
   - Decision: 6-stage security pipeline (SAST, SCA, Secrets, IaC, Container, DAST)
   - Consequences: Earlier vulnerability detection, longer build time

---

## 📈 Success Metrics

- **Zero** critical vulnerabilities in production
- **< 15 minutes** MTTR (Mean Time To Remediate) cho HIGH severity issues
- **100%** secrets stored in Azure Key Vault
- **Zero** publicly accessible database endpoints
- **All** traffic encrypted in transit (TLS 1.3)
- **< 5%** false positive rate cho security alerts

---

## 🔗 Tài liệu tham khảo

- [STRIDE Threat Modeling (Microsoft)](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool)
- [Azure Well-Architected Framework - Security](https://learn.microsoft.com/en-us/azure/architecture/framework/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Zero Trust Security Model (CISA)](https://www.cisa.gov/zero-trust-maturity-model)

---

Kế hoạch này cung cấp roadmap chi tiết để chuyển từ hệ thống hiện tại sang kiến trúc Zero Trust hoàn chỉnh với defense-in-depth và DevSecOps practices. Mỗi phase có deliverables cụ thể và measurable outcomes.
