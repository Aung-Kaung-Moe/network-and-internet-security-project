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

Rule and event mapping:

```text
Rule ID  Event type                    Response       Meaning
100500   honeypot_file_download        auto-ban       Forged-admin attacker downloaded bait CSV
100501   login_bruteforce_detected     review only    5 failed login attempts in 60 seconds
100502   webadmin_decoy_login          review only    webadmin/webadmin decoy login used
100503   webadmin_file_download        review only    webadmin decoy account downloaded bait CSV
100504   idor_probe_detected           review only    possible IDOR probe
100505   sql_injection_probe           review only    SQL injection probe
100506   scanner_user_agent            review only    scanner User-Agent detected
100507   path_bruteforce               review only    3 unrelated paths in 60 seconds
```

Only rule `100500` should be connected to the active response ban command. Rules `100501` through `100507` are SOC-review alerts and should not auto-ban accounts.

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

For IDOR probe alerts, search Wazuh Discover for:

```text
rule.id:100504
```

or:

```text
data.event_type:idor_probe_detected
```

The alert includes `target_object`, authenticated user fields when available, and the requested URL.

For SQL injection probe alerts, search Wazuh Discover for:

```text
rule.id:100505
```

or:

```text
data.event_type:sql_injection_probe
```

The alert includes `source`, `matched_patterns`, `matches`, and the inspected fields. Username and password fields are strict: single quote, double quote, backslash, SQL keywords such as `select`, `union`, `or`, `and`, `drop`, and tautologies such as `1=1` are alerted.

For scanner User-Agent alerts, search Wazuh Discover for:

```text
rule.id:100506
```

or:

```text
data.event_type:scanner_user_agent
```

The alert includes `user_agent`, `matched_keywords`, `srcip`, and the requested URL.

For path brute-force alerts, search Wazuh Discover for:

```text
rule.id:100507
```

or:

```text
data.event_type:path_bruteforce
```

This fires when the same source IP requests 3 unrelated paths in 60 seconds, whether the route is the same or different. The alert includes `attempted_paths`, `last_path`, `attempt_count`, and `window_seconds`.

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
