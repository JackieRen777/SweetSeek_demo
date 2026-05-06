import pexpect

password = None

# 1. Upload Nginx Conf
scp_cmd = "scp -o StrictHostKeyChecking=no production_nginx.conf root@sweetseek.top:/www/server/panel/vhost/nginx/sweetseek.top.conf"

# 2. Reload Nginx
reload_cmd = "ssh -o StrictHostKeyChecking=no root@sweetseek.top 'nginx -s reload'"

# 3. Restart Backend (Assuming python app.py)
# Kill old process and start new one in background
restart_cmd = "ssh -o StrictHostKeyChecking=no root@sweetseek.top 'pkill -f \"python3 app.py\"; cd /www/wwwroot/FCN_SweetSeek && nohup python3 app.py > app.log 2>&1 &'"

for cmd in [scp_cmd, reload_cmd, restart_cmd]:
    print(f"Exec: {cmd}")
    child = pexpect.spawn(cmd)
    try:
        i = child.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        if i == 0:
            if not password:
                print("Password is not set; skip interactive login.")
                raise SystemExit(1)
            child.sendline(password)
            child.expect(pexpect.EOF)
            print(child.before.decode())
        elif i == 1:
            print("Done")
    except Exception as e:
        print(f"Error: {e}")
