"""Email the AI-trends update to the user via Gmail.

Reads the Gmail app password from the GMAIL_APP_PASSWORD environment
variable (set once on this machine or as a GitHub Actions secret, never
stored in this folder).

Usage:
  python send_email.py "Subject line" body.txt
  python send_email.py "Subject line" body.txt --attach AI-TRENDS.md
  python send_email.py "Subject line" body.txt --html digest.html
"""

import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

# The account that owns the app password in GMAIL_APP_PASSWORD -- SMTP login
# and the app password must belong to the SAME account or Gmail returns 535.
# Overridable via env so the same script works locally and in CI.
TO_ADDRESS = os.environ.get("EMAIL_TO", "gbhambha@intelliai.net")
FROM_ADDRESS = os.environ.get("EMAIL_FROM", TO_ADDRESS)


def main():
    if len(sys.argv) < 3:
        print("usage: send_email.py SUBJECT BODY_FILE [--html FILE] [--attach FILE]")
        sys.exit(1)

    subject = sys.argv[1]
    body = Path(sys.argv[2]).read_text(encoding="utf-8")

    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        print("ERROR: GMAIL_APP_PASSWORD environment variable is not set.")
        sys.exit(1)
    # Google displays app passwords as "abcd efgh ijkl mnop"; tolerate a paste
    # that kept the spaces rather than failing to authenticate because of them.
    password = "".join(password.split())

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_ADDRESS
    msg["To"] = TO_ADDRESS
    msg.set_content(body)

    if "--html" in sys.argv:
        html_path = Path(sys.argv[sys.argv.index("--html") + 1])
        msg.add_alternative(html_path.read_text(encoding="utf-8"), subtype="html")

    if "--attach" in sys.argv:
        attach_path = Path(sys.argv[sys.argv.index("--attach") + 1])
        msg.add_attachment(
            attach_path.read_bytes(),
            maintype="text",
            subtype="markdown",
            filename=attach_path.name,
        )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(FROM_ADDRESS, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        # A raw traceback here is useless — 535 always means the credential is
        # wrong, so say what to actually check.
        print(f"ERROR: Gmail rejected the credentials for {FROM_ADDRESS}.")
        print(f"  SMTP said: {exc.smtp_code} {exc.smtp_error!r}")

        # Describe the SHAPE of the value without ever printing it. A real
        # Google app password is exactly 16 lowercase letters, no digits.
        problems = []
        if len(password) != 16:
            problems.append(f"length is {len(password)}, expected 16")
        if any(c.isdigit() for c in password):
            problems.append("contains digits — app passwords are letters only")
        if any(c.isupper() for c in password):
            problems.append("contains uppercase — app passwords are lowercase only")
        if not password.isalpha():
            problems.append("contains non-letter characters")

        if problems:
            print("  The stored value does NOT look like a Google app password:")
            for p in problems:
                print(f"    - {p}")
            print("  Regenerate one at https://myaccount.google.com/apppasswords")
        else:
            print("  The stored value IS shaped like a valid app password "
                  "(16 lowercase letters), so the value itself is not the "
                  "obvious problem. Most likely causes now:")
            print(f"   1. It was generated under a DIFFERENT Google account "
                  f"than {FROM_ADDRESS}.")
            print("      Check the account switcher before generating — being "
                  "signed into")
            print("      several Google accounts is the usual way this goes wrong.")
            print("   2. It was revoked or superseded after being stored.")
            print("   3. The account is Google Workspace and an admin has "
                  "disabled app")
            print("      passwords or SMTP access for it.")
        sys.exit(1)

    print(f"Email sent to {TO_ADDRESS}: {subject}")


if __name__ == "__main__":
    main()
