from app import create_app
from tasks import export_applications_csv, celery
import os, time
app = create_app()
EXPORT_DIR = os.path.join(app.config.get('UPLOAD_FOLDER','uploads'),'exports')
with app.app_context():
    t = export_applications_csv.apply_async(args=[None, 'admin'])
    print('Queued', t.id)
    waited=0
    while waited<30:
        res=celery.AsyncResult(t.id)
        print(' state=',res.state)
        if res.state in ('SUCCESS','FAILURE'):
            break
        time.sleep(1); waited+=1
    print('final', res.state)
    for f in os.listdir(EXPORT_DIR):
        if t.id in f:
            p=os.path.join(EXPORT_DIR,f)
            print('file',p,os.path.getsize(p))
            with open(p,'r',encoding='utf-8',errors='ignore') as fp:
                print('\n'.join(fp.read().splitlines()[:10]))
            break
