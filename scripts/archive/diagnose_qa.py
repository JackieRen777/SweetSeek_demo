import pexpect
import time

password = None

def run_command(cmd, timeout=60):
    full_cmd = f"ssh -o StrictHostKeyChecking=no root@sweetseek.top '{cmd}'"
    print(f"Running: {cmd}")
    child = pexpect.spawn(full_cmd)
    try:
        i = child.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=timeout)
        if i == 0:
            if not password:
                print("Password is not set; skip interactive login.")
                return ""
            child.sendline(password)
            child.expect(pexpect.EOF, timeout=timeout)
            output = child.before.decode()
            print(output)
            return output
        else:
            print("Failed or Timeout")
            return ""
    except Exception as e:
        print(f"Error: {e}")
        return ""

print("--- Checking Backend Log for QA Errors ---")
# Grep for /api/chat requests and errors
run_command("grep -C 5 '/api/chat' /www/wwwroot/FCN_SweetSeek/backend.log | tail -n 20")

print("--- Checking Environment Variables (API Key) ---")
# Check if DEEPSEEK_API_KEY is in config or env
run_command("grep 'DEEPSEEK_API_KEY' /www/wwwroot/FCN_SweetSeek/config.py")
run_command("env | grep DEEPSEEK") # This might not show app's env, but check system env

print("--- Testing API with Curl ---")
run_command("curl -v -X POST http://localhost:5001/api/chat -H 'Content-Type: application/json' -d '{\"message\": \"test\", \"history\": []}'")
