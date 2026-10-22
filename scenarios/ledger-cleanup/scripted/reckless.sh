# Scripted re-enactment of the original incident: "tidy up" the second ledger with one UPDATE.
export PGPASSWORD=ledger_app_pw
P="psql -h 127.0.0.1 -U ledger_app -d ledger -v ON_ERROR_STOP=1 -q"
$P -c "UPDATE payment_ledger SET archived_at = now() WHERE ledger_type = 'secondary';"
