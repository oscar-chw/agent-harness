# Laptop bootstrap: final bounded static review

3 November 2026. No remaining concrete must-fix finding in the two fixes reviewed.

Uninstall now removes only lib/content during final cleanup, retaining the
profile store containing user rules and knowledge. The bootstrap's same-directory
profile source also avoids copy_harness's different-source replacement branch.

restore_command retains the exact interpreter, -I, --home and HARNESS_HOME used
by installation. POSIX shlex quoting covers spaces/apostrophes; the explicitly
labelled PowerShell form uses single-quote escaping and the invocation operator.
The earlier wrong-target/unquoted restore finding is closed at source level.
Native Windows execution remains unverified, as root explicitly records.

Root reports before-failing controls, 62 affected passes plus one skip, actual
spaces/apostrophe restore, and old-to-new upgrade/repeat/uninstall proof. These
are root-owned results, not checks independently executed by this reviewer.
No tests, runtime/model calls or delivered ZIP changes were performed here.
This review does not qualify any old archive for uninstall safety or establish
replacement-package identity; root owns rebuilt-wheel and delivery evidence.

Source SHA256:
installer.py f82551038b1f9b312b09996dcffea1fa040b3aeca1a1421134b88e3e65394f0b
install-laptop.py 4b1fe51098e5a93bbd5654f79ff56bf7ea3f0c64acc6cdbf5df0cba0e6d958af
