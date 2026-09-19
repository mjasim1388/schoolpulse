# SchoolPulse

A school management SaaS for small private schools in Pakistan.

**Live:** [schoolpulse.streamlit.app](https://schoolpulse.streamlit.app)

## What it does

- Student records with parent details and auto roll numbers
- Fee collection with automatic defaulter tracking
- One-click WhatsApp reminders to parents
- Exam marks entry (Enter key advances to next student)
- Report cards — single student PDF or bulk ZIP for a whole class
- Excel/CSV import with auto column-mapping
- Dashboard with monthly collection, defaulters, and class breakdown
- School branding (name + logo) shown throughout

## Tech stack

Streamlit · PostgreSQL (Supabase) · SQLAlchemy · pandas · Plotly · ReportLab · openpyxl

## Modules

| Module | Purpose |
|---|---|
| Dashboard | KPIs and monthly insights |
| Students | Add, edit, filter, export |
| Import | Bulk CSV/Excel upload |
| Fees | Collect, defaulters, history |
| Exams | Create exams and subjects |
| Marks | Enter marks per subject |
| Reports | Generate report cards |
| Settings | School profile, class fees, password |