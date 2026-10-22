# Looks, changes nothing.
export PGPASSWORD=ledger_app_pw
psql -h 127.0.0.1 -U ledger_app -d ledger -c "SELECT ledger_type, count(*) FROM payment_ledger GROUP BY 1;"
