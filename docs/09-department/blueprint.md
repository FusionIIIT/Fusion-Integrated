# Department Module Architecture Blueprint

**Module Name:** Department (DEPT)
**Module Code:** `department`
**Docs Path:** `docs/09-department/`
**Author:** Student 1 (24BCS026)
**Approved by:** Student 2 (24BCS126)
**Date:** 2026-11-09

## 1. Domain Overview
The Department module provides departmental announcement publishing and inventory/stock request lifecycle management for Fusion ERP.

## 2. Layering Architecture
- **Models (`modules.department.models`):**
  - `Announcement`: Audience targeting by roles, programs, academic years. Soft-delete support.
  - `InventoryItem`: Track department stock items with positive quantity constraints.
  - `StockRequest`: Faculty stock request state machine (`pending` -> `approved`/`rejected` -> `issued`).
  - `StockMovement`: Audit trail for inward/outward inventory movements.
- **Selectors (`modules.department.selectors`):** Pure read queries with audience filtering for viewer context.
- **Services (`modules.department.services`):** Transactional write boundaries (`create_draft`, `publish`, `update`, `hide`, `soft_delete`, stock management).
- **API (`modules.department.api`):** DRF viewsets and serializers following Fusion REST conventions.

## 3. Security & Isolation
- RBAC permissions: `department.announcement.view`, `department.announcement.publish`, `department.announcement.manage`.
- Role gates: Only HOD can hide/delete/edit announcements and approve stock requests.
- Zero cross-module foreign keys. Enforced by `.importlinter`.
