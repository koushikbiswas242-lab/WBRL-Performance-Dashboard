# WBRL Performance Dashboard V3

## Full Upload → Database → Live Dashboard Connection

### Working flow
1. Upload Master Excel
2. Records are inserted or updated using AWC CODE
3. Upload ICA weekly Excel with week dates
4. Upload TPD weekly Excel with week dates
5. Data is stored in the database
6. Dashboard recalculates automatically

### Start the project
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open:
- Dashboard: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs

### Current production note
SQLite is included for local testing. For 100+ users and 19 districts, the production deployment should use PostgreSQL.
