Traceback (most recent call last):
  File "/home/joao/dev/orchestrator/scripts/sentinel.py", line 54, in <module>
    run_audit(target, base)
    ~~~~~~~~~^^^^^^^^^^^^^^
  File "/home/joao/dev/orchestrator/scripts/sentinel.py", line 23, in run_audit
    with open(os.path.join(ORCHESTRATOR_ROOT, "personas", "sentinel.md"), "r") as f:
         ~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/home/joao/dev/personas/sentinel.md'
