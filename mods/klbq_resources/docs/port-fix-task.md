# Final review fix: LAN port isolation

User scope: independent DST resource add-on only. No Git repository.

Final read-only review finding (P2): run_engine.py hardcodes 11041, but current LAN-only DST allows 10998 through 11018. Both engine logs warn Invalid port selection and silently fall back to 10999, which can collide with normal local servers.

Allowed files only:
- D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tools\run_engine.py
- D:\SOFTWARE\项目\饥荒\mods\klbq_resources\tests\test_engine_runner.py
- D:\SOFTWARE\项目\饥荒\mods\klbq_resources\docs\port-fix-report.md

Implement smallest robust fix:
- Introduce a choose_lan_port() helper which probes UDP bind on 127.0.0.1 in the allowed range 10998..11018. Prefer 11018 downward and skip 10999 (normal default).
- Close probe sockets reliably and fail clearly if no valid port available. Do not change or terminate any other process.
- Pass the chosen port consistently through server.ini and executable -port arguments.
- Reject Invalid port selection/fallback in engine output instead of accepting silently.
- Include chosen server_port in result JSON for audit.
- Do not change the runtime Lua, artwork, package or other project files.
- Use TDD. Add meaningful behavior tests calling the actual helper, including a held UDP socket to prove occupied ports are skipped. Record a missing-helper RED before implementing, then GREEN. No new dependencies.
- Parent separately reruns actual two-stage server test and updates docs, package count and final evidence. Do not run the actual engine from your task, since parent owns its temporary stage.
- Return concise status and write full RED/GREEN command/output report at docs/port-fix-report.md. Do not spawn additional agents.
