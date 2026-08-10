from tasks import celery, app
ids = ['a13830e9-9160-4a2e-b6e1-c46449d95f0c','a4d49c70-afe3-450e-95c8-4b8e87bffd00','a7912f6a-9464-4b23-899d-a0275b6f3c3d']
with app.app_context():
    for tid in ids:
        r = celery.AsyncResult(tid)
        print('Task', tid, 'state=', r.state, 'info=', r.info)
        if r.state == 'FAILURE':
            print('traceback:\n', r.traceback)
