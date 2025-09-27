    from app import app, db, User
    from werkzeug.security import generate_password_hash
    from datetime import datetime
    from app import Order

    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Tables created (if they didn't exist).")
        
        # Check if admin user exists, and create if not
        if not User.query.filter_by(username='admin').first():
            print("Creating admin user...")
            admin = User(username='admin', password=generate_password_hash('admin123'), role='admin')
            db.session.add(admin)
            db.session.commit()
            print("Admin user 'admin' created with password 'admin123'.")
        else:
            print("Admin user already exists.")

        # Check if a sample order exists, and create if not (optional, but good for testing)
        if not Order.query.first():
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                print("Creating sample order...")
                sample_order = Order(
                    details='Sample Order Details',
                    order_type='in',
                    date=datetime.now(),
                    product_name='Sample Product',
                    size='10cm x 20cm x 30cm',
                    quantity=5,
                    available_balance=5,
                    user_id=admin_user.id
                )
                db.session.add(sample_order)
                db.session.commit()
                print("Sample order created.")
            else:
                print("Admin user not found, cannot create sample order.")
        else:
            print("Sample order already exists.")

        db.session.close()
        print("Database initialization complete.")
    