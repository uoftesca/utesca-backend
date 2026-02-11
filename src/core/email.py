"""
DEPRECATED MODULE: `core.email` is implemented as a package (`core/email/`),
and this file (`core/email.py`) shadows that package and breaks imports like
`from core.email.service import EmailService`.

This module is intentionally disabled to avoid shadowing the `core.email`
package. Use the package submodules directly instead, for example:

    from core.email.service import EmailService

In the codebase, this file should be removed or renamed (for example to
`core/email/resend_service.py`) so that `core.email` remains a proper
package.
"""

raise ImportError(
    "The module 'core.email' defined by 'core/email.py' is deprecated and "
    "conflicts with the 'core.email' package. Please import from the "
    "'core.email' package instead, for example: "
    "'from core.email.service import EmailService'. "
    "This file should be removed or renamed (e.g. to 'core/email/resend_service.py')."
)
