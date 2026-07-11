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

Rule IDs:

```text
100500 = bait admin CSV downloaded; active response can ban this account
100501 = 5 failed login attempts in 60 seconds; SOC review only, no auto-ban
100502 = webadmin/webadmin decoy login used; SOC review only, no auto-ban
100503 = webadmin decoy account downloaded bait CSV; SOC review only, no auto-ban
```

For brute-force review alerts, search Wazuh Discover for:

```text
rule.id:100501
```

or:

```text
data.event_type:login_bruteforce_detected
```

The alert includes `attempted_credentials`, `last_attempt_username`, and `last_attempt_password` so analysts can inspect what the attacker tried.

For webadmin decoy-login alerts, search Wazuh Discover for:

```text
rule.id:100502
```

or:

```text
data.event_type:webadmin_decoy_login
```

The alert includes `attempted_username`, `attempted_password`, `srcip`, and the fake admin target URL.

For webadmin decoy download alerts, search Wazuh Discover for:

```text
rule.id:100503
```

or:

```text
data.event_type:webadmin_file_download
```

Do not add rule `100503` to the active response ban block. Only rule `100500` should auto-ban real attacker accounts that forged their own username into an admin JWT.

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
