# Ke Hoach Hoan Thanh Lab LangGraph (Cap Nhat cho repo hien tai)

## Tinh trang

- Repo: `2A202600103-LeNguyenChiBao-Day23`
- Da co Postgres Docker (`docker-compose.yml`)
- Da dong bo luong chay qua `venv` de tranh loi PATH/import
- Muc tieu: hoan tat TODO(student), dat diem cao voi persistence + recovery evidence

## Checklist trien khai

1. Chay bang Python trong `venv`

```powershell
.\venv\Scripts\pytest.exe
.\venv\Scripts\python.exe -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json
.\venv\Scripts\python.exe -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json
.\venv\Scripts\ruff.exe check src tests
.\venv\Scripts\mypy.exe src
```

2. Hoan thien TODO(student) trong code
- Giu nguyen dong TODO(student), chi cap nhat logic ben duoi.
- Bao gom: `nodes.py`, `routing.py`, `persistence.py`, `report.py`.

3. Persistence + recovery (uu tien Postgres)
- `CHECKPOINTER=postgres` va `DATABASE_URL` doc tu `.env`.
- Neu can, cai runtime:

```powershell
.\venv\Scripts\python.exe -m pip install "psycopg[binary]"
```

- Dung `thread_id` theo scenario va thu `get_state_history()` de chung minh recovery.

4. Metrics + report
- `outputs/metrics.json` hop le schema.
- `resume_success=true` khi co bang chung state-history.
- `reports/lab_report.md` tieng Anh, day du 8 muc theo template.

## Assumptions

- Khong hard-code scenario ID.
- Route dua tren keyword + state logic.
- Muc tieu nộp: pass test + metrics valid + report day du + persistence evidence.
