from app import app
c=app.test_client()
print('GET /api/estimator/merks', c.get('/api/estimator/merks').status_code, c.get('/api/estimator/merks').get_json())
print('GET /api/estimator/tipes?merk_id=1', c.get('/api/estimator/tipes?merk_id=1').get_json())
print('GET /api/estimator/keluhan?merk_id=1&tipe_id=1', c.get('/api/estimator/keluhan?merk_id=1&tipe_id=1').get_json())
print('GET /api/estimator/price?merk_id=1&tipe_id=1&keluhan=servis_rutin', c.get('/api/estimator/price?merk_id=1&tipe_id=1&keluhan=servis_rutin').get_json())
