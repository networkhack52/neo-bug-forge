def calculate_discount(price, discount_percent):
    """Apply a percentage discount to a price."""
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    discount = price * discount_percent / 100
    return price - discount


def format_price(amount):
    """Format a number as a price string."""
    return f"${amount:.2f}"
