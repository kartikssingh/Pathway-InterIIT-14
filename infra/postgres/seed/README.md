# Seed data

Optional demo data. `infra/bootstrap.sh` does **not** apply these — the schema
migrations and the two bootstrap admin accounts are all a working system needs.

Apply one when you want something to look at in the console:

```bash
docker exec -i db_tuto_postgres psql -U user -d values_db \
  < infra/postgres/seed/010_demo_users_and_transactions.sql
```

| File | What it inserts |
| --- | --- |
| `010_demo_users_and_transactions.sql` | A handful of users across every risk band, with transactions and alerts. |
| `020_load_test_data.sql` | A larger volume for `tests/load/locustfile.py`. |
| `030_monitoring_demo_data.sql` | Metrics, health checks and system alerts for the superadmin views. |

These are development fixtures. Never run them against anything holding real
customer data.
