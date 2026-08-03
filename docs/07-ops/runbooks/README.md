# Runbooks

One page each, copy-pasteable, **tested**. A runbook that has never been executed is a guess.

| Runbook | When | Tested |
|---|---|---|
| [provision-host.md](provision-host.md) | standing up a host for the first time | once per host |
| [deploy.md](deploy.md) | shipping a release | every deploy |
| [enable-scheduled-work.md](enable-scheduled-work.md) | turning on beat and the workers | once, after provisioning |
| [rollback.md](rollback.md) | a deploy went wrong | quarterly drill |
| [restore-from-backup.md](restore-from-backup.md) | data loss or corruption | **quarterly drill — mandatory, Phase 1 deliverable** |
| [rotate-signing-key.md](rotate-signing-key.md) | quarterly, or on suspected compromise | quarterly |
| [incident-auth-outage.md](incident-auth-outage.md) | users cannot log in | staging rehearsal, quarterly |
| [reingest-academic-snapshot.md](reingest-academic-snapshot.md) | ingest failed, or a CPI mismatch | on use |
| [sync-identity-projection.md](sync-identity-projection.md) | roles look stale, or the projection failed | **executed 2026-08-02 against live data** |
| [unlock-account.md](unlock-account.md) | a user is locked out | on use |

## Conventions

- Commands are copy-pasteable. Variables are `UPPER_CASE` and defined at the top.
- Every destructive step states **what it destroys** and how to undo it, before the command.
- Every runbook ends with a **verification** section. Finishing the steps is not the same as fixing the problem.
- Each has a **stop-and-escalate** line: the point at which you stop improvising.

## Before you start anything here

```bash
ssh fusion-vm
sudo -v                                     # confirm you have sudo
systemctl status fusion-iam fusion-platform fusion fusion-sysadmin --no-pager
df -h /var/lib/postgresql                   # the alert that matters most
journalctl -u fusion-platform --since '15 min ago' | grep -E 'ERROR|CRITICAL'
```

## Escalation

1. The on-call ops owner.
2. The platform lead — for anything touching migrations or the ERP.
3. The IAM lead — for anything touching auth, tokens or the projection.

**Stop and escalate rather than improvising when:** the ERP database (`fusion_newui_prod`) is involved · a
migration has partially applied · `reconcile_erp_projection --mode=enforce` would overwrite something you do
not understand · you are about to run anything with `DROP`, `TRUNCATE` or `--force`.

The ERP holds every student record in the institute and is owned by the legacy monolith. We only read it. If a
procedure seems to require writing to it, that is the signal to stop.
