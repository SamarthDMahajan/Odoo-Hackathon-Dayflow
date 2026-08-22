import app as app_module


def test_register_page_loads():
    app_module.app.config['TESTING'] = True
    app_module.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()

    client = app_module.app.test_client()
    response = client.get('/register')

    assert response.status_code == 200
    assert b'Register Account' in response.data


def test_register_creates_user():
    app_module.app.config['TESTING'] = True
    app_module.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()

    client = app_module.app.test_client()
    response = client.post('/register', data={
        'emp_id': 'EMP101',
        'name': 'Alice Admin',
        'email': 'alice@example.com',
        'password': 'secret123',
        'role': 'Admin / HR',
        'salary': '75000'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert app_module.User.query.filter_by(email='alice@example.com').count() == 1
