from flask_mail import Message
from src import mail

def send_email(subject, recipients, body):
    msg = Message(subject, recipients=recipients)
    msg.body = body  # Corrected this line
    mail.send(msg)

def send_purchase_details(user_email, product):
    msg = Message('Purchase Confirmation', recipients=[user_email])
    msg.body = f"""
    Dear Customer,

    Thank you for your purchase. Here are the details:

    Product Name: {product.name}
    Description: {product.description}
    Price: ${product.price}
    
    Login Details:
    Username: {user_email}
    Password: [Generated password here or user-defined]

    Regards,
    Marketplace Team
    """
    mail.send(msg)