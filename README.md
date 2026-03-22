---

## Project Summary (Copy this to continue elsewhere)

---

**CaseIQ Backend — Completed**

Django 5.1 + DRF + PostgreSQL 17 + Groq AI

**Stack:** Django, DRF, SimpleJWT, PostgreSQL, pgvector (pending), Redis (pending), Celery, Groq API, Gemini Embeddings, NewsAPI, ReportLab PDF

**Path:** `D:\BCA\MCA\SHREE\caseiq-backend`

**Running:** `python manage.py runserver` → `http://127.0.0.1:8000`

**All API Endpoints:**
```
POST   /api/v1/auth/register/
POST   /api/v1/auth/login/
POST   /api/v1/auth/logout/
GET    /api/v1/auth/profile/
PUT    /api/v1/auth/profile/
POST   /api/v1/auth/change-password/
POST   /api/v1/auth/token/refresh/

POST   /api/v1/legal/query/
GET    /api/v1/legal/query/history/
GET    /api/v1/legal/query/<id>/
GET    /api/v1/legal/sections/

POST   /api/v1/knowledge/search/
GET    /api/v1/knowledge/provisions/
GET    /api/v1/knowledge/categories/
GET    /api/v1/knowledge/rights/

POST   /api/v1/complaints/draft/
GET    /api/v1/complaints/history/
GET    /api/v1/complaints/<id>/
GET    /api/v1/complaints/<id>/download/

GET    /api/v1/awareness/news/
GET    /api/v1/awareness/news/<id>/
POST   /api/v1/awareness/news/fetch/
GET    /api/v1/awareness/education/
GET    /api/v1/awareness/education/<id>/

GET    /api/docs/  ← Swagger UI
```

**Models:** User (UUID, roles, multilingual), LegalQuery, QueryResponse, BNSSSection (1641 sections), LegalProvision, LegalCategory, Complaint, LegalNewsArticle, EducationalContent, AuditLog, EthicsRule, DisclaimerTemplate

**Key Features Done:**
- JWT auth with token blacklist + refresh
- Groq Llama 3.3 70B for legal queries
- Ethical AI filter (blocks advisory content)
- BNS/BNSS/IPC/CrPC/BSA — 1641 sections ingested from PDFs
- FIR/Complaint generator with ReportLab PDF export (trilingual)
- Legal news feed with Groq auto-tagging
- Educational content seeded (4 articles)
- Celery tasks scheduled (news fetch every 6h, audit cleanup daily)
- Full Swagger docs at /api/docs/

**Pending:** pgvector (Docker build issue on Windows), Redis local install

---

**CaseIQ Frontend — Setup Pending**

React + Vite, port 8080

**Path:** `D:\BCA\MCA\SHREE\CaseIQ\caseiq-frontend`

**Structure:**
```
src/
  components/
    ai/       → AIResponseWindow, QueryInput
    dashboard/ → HistoryPanel, RecentSearches
    education/ → AwarenessCards, RightsSection
    fir/       → FIRForm, FIRPreview, FIRDownload (jsPDF)
    law/       → LawCard, LawReferenceViewer
    layout/    → Header, Sidebar, Footer, DisclaimerBar, Layout
    ui/        → Button, Card, Input, Loader, Modal, Textarea, ToggleSwitch
  context/
    AuthContext.jsx     → Currently fake (localStorage only)
    SettingsContext.jsx → Dark mode, language, font size ✅
  hooks/
    useQuery.js    → Currently simulated
    useAccessibility.js
    useLanguage.js
  pages/
    HomePage, ChatPage, FIRDraftPage, DashboardPage,
    EducationPage, HistoryPage, LoginPage, SettingsPage
  routes/
    AppRoutes.jsx → Protected routes, redirects to Login if no user
  utils/
    constants.js, validation.js, formatDate.js


Integration Plan:

Create src/services/api.js — Axios + all API calls
Update AuthContext.jsx — Real JWT login/register/logout
Create RegisterPage.jsx — New page
Update LoginPage.jsx — Add password + register link
Update ChatPage.jsx — Call real Groq AI via backend
Update FIRDraftPage.jsx — Backend draft + keep jsPDF
Update HistoryPage.jsx — Backend history for logged-in users
Update DashboardPage.jsx — Real counts from backend
Update EducationPage.jsx — Backend awareness content
Update AppRoutes.jsx — Add register route

Decisions made:

Guest users → localStorage fallback
Logged-in users → backend sync
Keep jsPDF + add backend PDF download
Add Register page + password to Login
Google OAuth to add later