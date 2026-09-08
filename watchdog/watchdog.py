"""DISTI container watchdog, following VENTI retry/cooldown semantics."""
import logging, os, time
from collections import deque
import docker, psycopg2, requests
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG=logging.getLogger("disti-watchdog")
class Watchdog:
 def __init__(self, client=None, http=requests, clock=time.monotonic, sleep=time.sleep):
  self.client=client or docker.from_env();self.http=http;self.clock=clock;self.sleep=sleep;self.last_restart={};self.restarts=deque();self.last_alert={}
  self.backend=os.getenv("WATCHDOG_BACKEND_CONTAINER","flask-backend");self.database=os.getenv("WATCHDOG_DATABASE_CONTAINER","disti-postgres");self.hardware=os.getenv("WATCHDOG_HARDWARE_CONTAINER","disti-hardware-agent")
  self.health=os.getenv("WATCHDOG_BACKEND_HEALTH_URL","http://backend:5000/healthz");self.status=os.getenv("WATCHDOG_STATUS_URL","http://backend:5000/watchdog/status")
  self.cooldown=int(os.getenv("WATCHDOG_COOLDOWN_SEC","120"));self.budget=int(os.getenv("WATCHDOG_MAX_RESTARTS_PER_HOUR","4"));self.recheck=int(os.getenv("WATCHDOG_BACKEND_RECHECK_SEC","2"));self.recovery=int(os.getenv("WATCHDOG_RECOVERY_WAIT_SEC","30"));self.retries=int(os.getenv("WATCHDOG_BACKEND_RETRIES","3"));self.alert_cooldown=int(os.getenv("WATCHDOG_ALERT_COOLDOWN_SEC","900"))
 def get(self,url): return self.http.get(url,timeout=10)
 def healthy(self):
  try:return self.get(self.health).ok
  except Exception:return False
 def alert(self,key,message):
  now=self.clock()
  if now-self.last_alert.get(key,-self.alert_cooldown)>=self.alert_cooldown:LOG.error(message);self.last_alert[key]=now
 def can_restart(self,name):
  now=self.clock()
  while self.restarts and now-self.restarts[0]>3600:
   self.restarts.popleft()
  return now-self.last_restart.get(name,-self.cooldown)>=self.cooldown and len(self.restarts)<self.budget
 def restart(self,name):
  if not self.can_restart(name):self.alert(name+"-budget",f"Restart suppressed for {name}: cooldown/budget");return False
  container=self.client.containers.get(name);container.reload();LOG.warning("%s state=%s",name,container.attrs.get("State"));LOG.warning("%s recent logs:\n%s",name,container.logs(tail=50).decode(errors="replace"));container.restart()
  now=self.clock();self.last_restart[name]=now;self.restarts.append(now);return True
 def database_healthy(self):
  try:
   conn=psycopg2.connect(host=os.environ["POSTGRES_HOST"],database=os.environ["POSTGRES_DB"],user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],connect_timeout=5);conn.close();return True
  except Exception:return False
 def check(self):
  if not self.healthy():
   self.sleep(self.recheck)
   if not self.healthy() and self.restart(self.backend):
    self.sleep(self.recovery)
    for _ in range(self.retries):
     if self.healthy():return
     self.sleep(self.recheck)
    self.alert("backend-recovery","Backend did not recover after restart")
   return
  try:
   response=self.get(self.status);response.raise_for_status();status=response.json()
  except Exception:
   if not self.database_healthy():self.restart(self.database)
   return
  if not status.get("database",{}).get("healthy",False):self.restart(self.database)
  elif not status.get("hardware_agent",{}).get("healthy",False):self.restart(self.hardware)
 def run(self):
  interval=int(os.getenv("WATCHDOG_CHECK_INTERVAL_SEC","30"))
  while True:
   try:self.check()
   except Exception:LOG.exception("Watchdog check failed")
   self.sleep(interval)
if __name__=="__main__":Watchdog().run()
