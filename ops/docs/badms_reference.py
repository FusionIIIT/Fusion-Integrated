"""BADMS reference entrypoint for module review check."""

import runpy

if __name__ == "__main__":
    runpy.run_module("ops.docs.badms_teaching_reference", run_name="__main__")
