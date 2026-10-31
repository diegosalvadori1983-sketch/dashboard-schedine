#!/usr/bin/env python3
"""Monitora i punteggi ESPN e invia a ntfy solo le variazioni osservate."""
import json, os, urllib.request, urllib.error
from pathlib import Path

TOPIC = os.environ.get('NTFY_TOPIC', '').strip()
STATE = Path('stato_risultati.json')
GAMES = [
 ('Werder Bremen','Hoffenheim','ger.1','20261031'),
 ('Union Berlin','Cologne','ger.1','20261101'),
 ('Bournemouth','Leeds United','eng.1','20261031'),
 ('Bayern Munich','Borussia Dortmund','ger.1','20261031'),
 ('AC Milan','Inter Milan','ita.1','20261031'),
 ('Udinese','AS Roma','ita.1','20261031'),
 ('Como','Venezia','ita.1','20261101'),
 ('Lazio','Cagliari','ita.1','20261101'),
 ('Barcelona','Alaves','esp.1','20261031'),
 ('Manchester City','Brighton','eng.1','20261031'),
]
ALIAS = {'cologne':['koln','koeln','cologne'], 'acmilan':['milan'], 'intermilan':['inter','internazionale'], 'asroma':['roma'], 'bayernmunich':['bayern'], 'borussiadortmund':['dortmund'], 'leedsunited':['leeds'], 'werderbremen':['werder'], 'barcelona':['barcelona'], 'manchestercity':['manchestercity']}
def norm(s):
 import unicodedata
 s=unicodedata.normalize('NFD',str(s or '').lower())
 return ''.join(c for c in s if c.isalnum() and not unicodedata.combining(c))
def same(a,b):
 x,y=norm(a),norm(b)
 return any(y==v or (len(v)>=5 and v in y) for v in ALIAS.get(x,[x]))
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'SchedineMonitor/1.0'})
 with urllib.request.urlopen(req,timeout=20) as response: return json.load(response)
def notify(title,message):
 if not TOPIC: raise RuntimeError('Secret NTFY_TOPIC mancante')
 req=urllib.request.Request('https://ntfy.sh/'+TOPIC,data=message.encode('utf-8'),headers={'Title':title.encode('ascii','ignore').decode('ascii'), 'Tags':'soccer', 'Priority':'default'},method='POST')
 with urllib.request.urlopen(req,timeout=20) as response: response.read()
def main():
 previous=json.loads(STATE.read_text()) if STATE.exists() else {}
 current=dict(previous)
 all_events={}
 for league,date in sorted(set((x[2],x[3]) for x in GAMES)):
  try:
   data=fetch(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date}&limit=200')
   all_events[(league,date)]=data.get('events',[])
  except Exception as exc:
   print('Fonte temporaneamente non disponibile',league,date,exc)
 for home,away,league,date in GAMES:
  key=f'{league}|{date}|{norm(home)}|{norm(away)}'
  for event in all_events.get((league,date),[]):
   comps=event.get('competitions',[{}])[0].get('competitors',[])
   h=next((x for x in comps if x.get('homeAway')=='home'),None)
   a=next((x for x in comps if x.get('homeAway')=='away'),None)
   if not h or not a or not same(home,h.get('team',{}).get('displayName')) or not same(away,a.get('team',{}).get('displayName')):continue
   if h.get('score') is None or a.get('score') is None:break
   score=f"{h['score']}-{a['score']}"
   status=event.get('status',{}).get('type',{}).get('state')
   old=previous.get(key)
   if old is not None and old!=score and status in ('in','post'):
    notify('Cambio risultato!',f'{home} - {away}: {old} -> {score}. Controlla la dashboard per i dettagli.')
    print('Notifica inviata',home,away,old,score)
   current[key]=score
   break
 # Salva solo le partite effettivamente trovate; conserva lo stato per errori temporanei.
 STATE.write_text(json.dumps(current,ensure_ascii=False,indent=2))
 print('Partite monitorate:',len(current),'su',len(GAMES))
if __name__=='__main__':main()
