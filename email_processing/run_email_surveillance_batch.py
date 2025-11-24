import os
import sys
import subprocess
from datetime import datetime


def ymd(d: datetime) -> str:
    return d.strftime('%Y-%m-%d')


def ddmmyyyy(d: datetime) -> str:
    return d.strftime('%d%m%Y')


def run_for_date(date_obj: datetime, model: str) -> dict:
    date_ymd = ymd(date_obj)
    date_ddmmyyyy = ddmmyyyy(date_obj)

    env = os.environ.copy()
    env['EMAIL_MODEL'] = 'o3' if model.lower() in ('o3', 'o3-mini', 'o3_mini') else 'gpt-4.1'

    # 1) Fetch/process emails for date (this will also run the AI and write email_surveillance_YYYYMMDD.json)
    print(f"\n=== [{model}] Processing emails for {date_ymd} ===")
    proc = subprocess.run([
        sys.executable, 'email_processing/process_emails_by_date.py', date_ymd
    ], env=env, cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    if proc.returncode != 0:
        return {"date": date_ymd, "status": "fail", "matched": 0, "groups": 0}

    # 2) Copy to DDMMYYYY filename expected by validator
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    src = os.path.join(root, f'email_surveillance_{date_obj.strftime("%Y%m%d")}.json')
    dst = os.path.join(root, f'email_surveillance_{date_ddmmyyyy}.json')
    if os.path.exists(src):
        subprocess.run(['cp', '-f', src, dst], cwd=root)

    # 3) Run validator to update Excel and compute matches
    print(f"=== [{model}] Running validator for {date_ddmmyyyy} ===")
    proc2 = subprocess.run([
        sys.executable, 'email_order_validation_august_daily.py', date_ddmmyyyy
    ], env=env, cwd=root, capture_output=True, text=True)
    matched = 0
    groups = 0
    out = proc2.stdout + "\n" + proc2.stderr
    for line in out.splitlines():
        if 'Matched Instructions:' in line:
            try:
                matched = int(line.strip().split(':')[-1])
            except Exception:
                pass
        if 'Total Email Groups:' in line:
            try:
                groups = int(line.strip().split(':')[-1])
            except Exception:
                pass

    return {"date": date_ymd, "status": "ok", "matched": matched, "groups": groups}


def main():
    # Args: --model o3|gpt-4.1  [optional: --start 2025-09-01 --end 2025-09-10]
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True, choices=['o3', 'gpt-4.1'])
    parser.add_argument('--start', default='2025-09-01')
    parser.add_argument('--end', default='2025-09-10')
    args = parser.parse_args()

    start = datetime.strptime(args.start, '%Y-%m-%d')
    end = datetime.strptime(args.end, '%Y-%m-%d')

    results = []
    from datetime import timedelta
    d = start
    while d <= end:
        results.append(run_for_date(d, args.model))
        d = d + timedelta(days=1)

    # Print summary
    print(f"\n=== SUMMARY [{args.model}] ===")
    total_matched = sum(r.get('matched', 0) for r in results)
    total_groups = sum(r.get('groups', 0) for r in results)
    for r in results:
        print(f"{r['date']}: matched={r['matched']} groups={r['groups']} status={r['status']}")
    print(f"TOTAL matched={total_matched} across {len(results)} days; TOTAL groups={total_groups}")


if __name__ == '__main__':
    main()


