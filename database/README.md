# Database

This project uses **PostgreSQL** as its primary database, managed through SQLAlchemy
models (`backend/app/models/`) and Alembic migrations (`backend/alembic/versions/`).

No standalone SQL schema files are kept here — the migrations in `backend/alembic/versions/`
are the source of truth for the schema. To create the database and apply the schema:

```powershell
psql -U postgres
CREATE DATABASE interview_coach;
\q

cd backend
python -m alembic upgrade head
python -m scripts.seed   # optional: adds demo data
```

See the top-level README.md for full installation instructions.
