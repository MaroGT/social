from src import create_app, db
from src.models import Product

# Create the app instance using your factory function
app = create_app()

# Run the code within the app context
with app.app_context():
    # Create demo products
    product1 = Product(
        name="Product 1",
        description="A great product with fantastic features.",
        price=10.0,
        category="Electronics",
        stock=5,
        login=None
    )

    product2 = Product(
        name="Product 2",
        description="Another excellent product with amazing specs.",
        price=20.0,
        category="Home Goods",
        stock=10,
        login=None
    )

    product3 = Product(
        name="Product 3",
        description="An essential item for everyone.",
        price=30.0,
        category="Beauty",
        stock=2,
        login=None
    )

    # Add products to the database
    db.session.add_all([product1, product2, product3])
    db.session.commit()

    print("Demo products added successfully!")
