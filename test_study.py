import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import study

class Tests(unittest.TestCase):
    def test_eight_conditions_and_prompts(self):
        c=study.config()
        self.assertEqual(len(study.conditions(c)),8)
        self.assertEqual(study.prompt_for(c,'P1')['instructions'],'')
        self.assertEqual(len(set((x['prompt'],x['temperature']) for x in study.conditions(c))),8)

    def test_time_boundary(self):
        c=study.config();s=study.new_session('anon',1,study.conditions(c)[0],c)
        t=s['started']
        self.assertEqual(study.phase(s,t+299),'active')
        self.assertEqual(study.phase(s,t+300),'final')
        self.assertEqual(study.phase(s,t+360),'final')
        self.assertEqual(study.phase(s,t+361),'expired')
        s['closed']=True
        self.assertEqual(study.phase(s,t+305),'closed')

    def test_database_saves_transcripts_and_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(study,'DB',Path(tmp)/'test.db'):
                c=study.config();p=study.participant('70–79','Prefer not to say','None')
                assigned=study.assign(p,c)
                self.assertEqual(len(assigned),2)
                s=study.new_session(p,1,assigned[0],c)
                s['turns']=1
                s['turn_data']=[dict(n=1,user='Hello',ai='Hi',mode='voice',latency=.6,timestamp=0)]
                study.save_session(s,{k:5 for k,_ in study.QUESTIONS},'', 'Yes','gpt-4o-mini','marin')
                study.save_reviews(s,{1:{'rating':'Good','standout':True}})
                with study.database() as db:
                    self.assertEqual(db.execute('select count(*) from turns').fetchone()[0],1)
                    self.assertEqual(db.execute('select rating from turn_reviews').fetchone()[0],'Good')
                    self.assertEqual(db.execute('select count(*) from sessions').fetchone()[0],1)

if __name__=='__main__': unittest.main()
