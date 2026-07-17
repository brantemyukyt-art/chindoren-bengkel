from app import app

c = app.test_client()
r = c.get('/', follow_redirects=True)
print('Status:', r.status_code)
print('Request path:', r.request.path)
body = r.get_data(as_text=True)
print('Body length:', len(body))
print('-----BODY START-----')
print(body)
print('-----BODY END-----')
