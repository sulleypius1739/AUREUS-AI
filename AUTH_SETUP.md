# AUREUS authentication and President admin

Run the web app from the project root with:

    node server.js

Then open:

    http://localhost:8000

On first run, if `data/auth/users.json` does not exist, AUREUS creates a President account. If `ADMIN_EMAIL` and `ADMIN_PASSWORD` are not set, the server prints the one-time generated password in the terminal. Change it before using the system beyond local testing.

For a fixed first-run admin account, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the environment before starting the server. Do not commit real credentials.

The President can use **Admin Console** to create users with USER, ANALYST, or ADMIN roles and enable/disable non-President accounts. Audit events are written to `data/auth/audit.json` locally; both user and audit stores are ignored by Git.

The browser uses HttpOnly session cookies. The live market-data API key remains a client-side provider credential in the existing live-data panel; move that provider key behind a server-side proxy before deploying publicly.
