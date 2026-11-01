"""Unit tests for BADMS state machines and workflow transitions.

Covers:
- CW-BA-01: Secure Archival Request Processing (BW-BA-01, BW-BA-02, BW-BA-03)
- CW-BA-02: Storage-Extension Request Processing (BW-BA-04, BW-BA-05)
- CW-BA-03: Data Restoration Processing (BW-BA-06, BW-BA-07)
"""

import unittest
from ..domain import (
    ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    ARCHIVAL_CLASSIFIED_SENSITIVE,
    ARCHIVAL_ENCRYPTED,
    ARCHIVAL_HOD_APPROVED,
    ARCHIVAL_NOT_SUBMITTED,
    ARCHIVAL_REJECTED,
    ARCHIVAL_SUBMITTED,
    CLASS_CRITICAL,
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    DomainValidationError,
    EXT_APPROVED,
    EXT_NOT_SUBMITTED,
    EXT_REJECTED,
    EXT_SUBMITTED,
    RESTORE_APPROVED_FOR_EXECUTION,
    RESTORE_COMPLETED,
    RESTORE_NOT_REQUESTED,
    RESTORE_REJECTED,
    RESTORE_SENSITIVE_PENDING,
    RESTORE_STANDARD_PENDING,
    ArchivalWorkflowEngine,
    RestorationWorkflowEngine,
    StorageExtensionWorkflowEngine,
)


class BadmsWorkflowTestCase(unittest.TestCase):

    def test_cw_ba_01_bw_01_hod_rejection_workflow(self):
        """BW-BA-01: Not Submitted -> Submitted -> Rejected by HoD."""
        s1 = ArchivalWorkflowEngine.transition_submit(ARCHIVAL_NOT_SUBMITTED)
        self.assertEqual(s1, ARCHIVAL_SUBMITTED)

        s2 = ArchivalWorkflowEngine.transition_hod_decision(s1, approved=False)
        self.assertEqual(s2, ARCHIVAL_REJECTED)

    def test_cw_ba_01_bw_02_non_sensitive_archival_workflow(self):
        """BW-BA-02: Not Submitted -> Submitted -> HoD Approved -> Non-Sensitive Policy Applied."""
        s1 = ArchivalWorkflowEngine.transition_submit(ARCHIVAL_NOT_SUBMITTED)
        s2 = ArchivalWorkflowEngine.transition_hod_decision(s1, approved=True)
        self.assertEqual(s2, ARCHIVAL_HOD_APPROVED)

        # SysAdmin assigns Routine classification
        s3 = ArchivalWorkflowEngine.transition_sysadmin_classification(s2, CLASS_ROUTINE)
        self.assertEqual(s3, ARCHIVAL_CLASSIFIED_NON_SENSITIVE)

    def test_cw_ba_01_bw_03_sensitive_encryption_workflow(self):
        """BW-BA-03: Not Submitted -> Submitted -> HoD Approved -> Sensitive / Routed -> Encrypted."""
        s1 = ArchivalWorkflowEngine.transition_submit(ARCHIVAL_NOT_SUBMITTED)
        s2 = ArchivalWorkflowEngine.transition_hod_decision(s1, approved=True)
        
        # SysAdmin assigns Sensitive classification
        s3 = ArchivalWorkflowEngine.transition_sysadmin_classification(s2, CLASS_SENSITIVE)
        self.assertEqual(s3, ARCHIVAL_CLASSIFIED_SENSITIVE)

        # IT Security configures encryption
        s4 = ArchivalWorkflowEngine.transition_it_security_encryption(s3)
        self.assertEqual(s4, ARCHIVAL_ENCRYPTED)

    def test_cw_ba_02_storage_extension_workflows(self):
        """CW-BA-02: Submit -> HoD Approve (BW-BA-05) / HoD Reject (BW-BA-04)."""
        s1 = StorageExtensionWorkflowEngine.transition_submit(EXT_NOT_SUBMITTED)
        self.assertEqual(s1, EXT_SUBMITTED)

        # Approve branch
        s_appr = StorageExtensionWorkflowEngine.transition_hod_decision(s1, approved=True)
        self.assertEqual(s_appr, EXT_APPROVED)

        # Reject branch
        s_rej = StorageExtensionWorkflowEngine.transition_hod_decision(s1, approved=False)
        self.assertEqual(s_rej, EXT_REJECTED)

    def test_cw_ba_03_restoration_workflows(self):
        """CW-BA-03: Standard Path (BW-BA-06) vs Sensitive Path (BW-BA-07)."""
        # Standard path (Non-sensitive)
        r_std = RestorationWorkflowEngine.transition_request(RESTORE_NOT_REQUESTED, is_sensitive=False)
        self.assertEqual(r_std, RESTORE_STANDARD_PENDING)

        r_comp = RestorationWorkflowEngine.transition_execution(r_std)
        self.assertEqual(r_comp, RESTORE_COMPLETED)

        # Sensitive path (requires SysAdmin approval)
        r_sens = RestorationWorkflowEngine.transition_request(RESTORE_NOT_REQUESTED, is_sensitive=True)
        self.assertEqual(r_sens, RESTORE_SENSITIVE_PENDING)

        # Attempting execution before approval must raise error
        with self.assertRaises(DomainValidationError):
            RestorationWorkflowEngine.transition_execution(r_sens)

        # SysAdmin approves
        r_appr = RestorationWorkflowEngine.transition_sysadmin_approval(r_sens, approved=True)
        self.assertEqual(r_appr, RESTORE_APPROVED_FOR_EXECUTION)

        # Execution succeeds
        r_done = RestorationWorkflowEngine.transition_execution(r_appr)
        self.assertEqual(r_done, RESTORE_COMPLETED)


if __name__ == "__main__":
    unittest.main()
