import unittest
from app import app, db, User, Order, Production, Inventory
from werkzeug.security import generate_password_hash

class ElMasaTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()
            # Create sample users
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            orders_user = User(username='Ahmed', password=generate_password_hash('ahmed123'), role='orders')
            production_user = User(username='Ashraf', password=generate_password_hash('ashraf123'), role='production')
            inventory_user = User(username='Mohammed', password=generate_password_hash('mohammed123'), role='inventory')
            db.session.add_all([admin, orders_user, production_user, inventory_user])
            db.session.commit()

    def login(self, username, password):
        return self.app.post('/login', data=dict(username=username, password=password), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_login_logout(self):
        rv = self.login('admin', 'admin123')
        self.assertIn(b'Welcome, admin', rv.data)
        rv = self.logout()
        self.assertIn(b'Login', rv.data)

    def test_role_access(self):
        # Orders user can access orders but not production
        self.login('Ahmed', 'ahmed123')
        rv = self.app.get('/orders')
        self.assertEqual(rv.status_code, 200)
        rv = self.app.get('/production')
        self.assertEqual(rv.status_code, 302)  # Redirect to index
        self.logout()

        # Production user can access production but not inventory
        self.login('Ashraf', 'ashraf123')
        rv = self.app.get('/production')
        self.assertEqual(rv.status_code, 200)
        rv = self.app.get('/inventory')
        self.assertEqual(rv.status_code, 302)
        self.logout()

        # Inventory user can access inventory but not orders
        self.login('Mohammed', 'mohammed123')
        rv = self.app.get('/inventory')
        self.assertEqual(rv.status_code, 200)
        rv = self.app.get('/orders')
        self.assertEqual(rv.status_code, 302)
        self.logout()

    def test_crud_order(self):
        self.login('Ahmed', 'ahmed123')
        # Add order
        rv = self.app.post('/add_order', data=dict(
            details='Test Order',
            receive_date='2023-10-01',
            product_name='Test Product',
            size='M',
            quantity=10
        ), follow_redirects=True)
        self.assertIn(b'Test Order', rv.data)
        # Edit order
        with app.app_context():
            order = Order.query.filter_by(details='Test Order').first()
            self.assertIsNotNone(order)
            rv = self.app.post(f'/edit_order/{order.id}', data=dict(
                details='Updated Order',
                receive_date='2023-10-02',
                product_name='Test Product',
                size='M',
                quantity=15
            ), follow_redirects=True)
            self.assertIn(b'Updated Order', rv.data)
            # Delete order
            rv = self.app.post(f'/delete_order/{order.id}', follow_redirects=True)
            self.assertNotIn(b'Updated Order', rv.data)
        self.logout()

    def test_crud_production(self):
        self.login('Ashraf', 'ashraf123')
        # Add production
        rv = self.app.post('/add_production', data=dict(
            details='Test Production',
            date='2023-10-01',
            product_name='Test Product',
            size='M',
            quantity=20
        ), follow_redirects=True)
        self.assertIn(b'Test Production', rv.data)
        # Edit production
        with app.app_context():
            production = Production.query.filter_by(details='Test Production').first()
            self.assertIsNotNone(production)
            rv = self.app.post(f'/edit_production/{production.id}', data=dict(
                details='Updated Production',
                date='2023-10-02',
                product_name='Test Product',
                size='M',
                quantity=25
            ), follow_redirects=True)
            self.assertIn(b'Updated Production', rv.data)
            # Delete production
            rv = self.app.post(f'/delete_production/{production.id}', follow_redirects=True)
            self.assertNotIn(b'Updated Production', rv.data)
        self.logout()

    def test_crud_inventory(self):
        self.login('Mohammed', 'mohammed123')
        # Add inventory
        rv = self.app.post('/add_inventory', data=dict(
            item_type='box',
            quantity=30,
            action='in',
            date='2023-10-01',
            product_name='Test Product',
            size='M'
        ), follow_redirects=True)
        self.assertIn(b'Inventory', rv.data)
        # Edit inventory
        with app.app_context():
            inventory = Inventory.query.filter_by(product_name='Test Product').first()
            self.assertIsNotNone(inventory)
            rv = self.app.post(f'/edit_inventory/{inventory.id}', data=dict(
                item_type='carton',
                quantity=35,
                action='out',
                date='2023-10-02',
                product_name='Test Product',
                size='M'
            ), follow_redirects=True)
            self.assertIn(b'Inventory', rv.data)
            # Delete inventory
            rv = self.app.post(f'/delete_inventory/{inventory.id}', follow_redirects=True)
            self.assertNotIn(b'Inventory', rv.data)
        self.logout()

if __name__ == '__main__':
    unittest.main()
