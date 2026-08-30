#!/usr/bin/env python3
"""Run one guarded Macleen's AI Marketing scheduler iteration.

Useful for a Render Cron Job if you prefer a private cron process instead of the
protected HTTP endpoint used by UptimeRobot.
"""
from app import app, run_db_setup, run_marketing_agent_once

if __name__ == '__main__':
    with app.app_context():
        run_db_setup()
        print(run_marketing_agent_once())
