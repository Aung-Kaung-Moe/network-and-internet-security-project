# Wazuh Hook Notes

The honeypot writes one JSON object per line to:

```text
logs/wazuh-honeypot-alerts.jsonl
```

When an attacker downloads a bait CSV from the fake admin service, the event includes fields such as:

```json
{
  "honeypot_program": "northstar-library-honeypot",
  "event_type": "honeypot_file_download",
  "attacker_username": "attacker",
  "account_to_ban": "attacker",
  "file": "credentials",
  "owner_action": "ban_candidate"
}
```

Use `ossec-localfile-example.xml` to monitor this JSONL file, and `local_rules.xml` to raise a Wazuh alert.

For automatic banning, copy `ban-library-account.cmd` into the Windows Wazuh Agent active response directory:

```text
C:\Program Files (x86)\ossec-agent\active-response\bin\ban-library-account.cmd
```

Then add the command and active response blocks from `active-response-example.xml` to the Wazuh Manager config and restart the manager.

The launcher calls `backend/ban_account.py`. The script accepts either:

```powershell
python backend/ban_account.py attacker
```

or a Wazuh-style alert JSON on stdin. It inserts the username into the app database `banned_accounts` table. After that, the real site rejects that account during login/token checks.
