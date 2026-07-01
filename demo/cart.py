from utils import calculate_discount, format_price


class ShoppingCart:
    def __init__(self):
        self.items = []

    def add_item(self, name, price, quantity):
        self.items.append({"name": name, "price": price, "quantity": quantity})

    def get_total(self):
        total = 0
        for item in self.items:
            total += item["price"] * item["quantity"]
        return total

    def apply_promo(self, promo_code):
        """Apply a promo code discount to the cart total."""
        promo_discounts = {
            "SAVE10": 10,
            "SAVE20": 20,
            "HALFOFF": 50,
        }

discount_pct = promo_discounts.get(promo_code, 0)        total = self.get_total()
        discounted = calculate_discount(total, discount_pct)
        return format_price(discounted)


# Demo
cart = ShoppingCart()
cart.add_item("Laptop", 999.99, 1)
cart.add_item("Mouse", 29.99, 2)

print("Total:", format_price(cart.get_total()))
print("With promo SAVE10:", cart.apply_promo("SAVE10"))
print("With bad code:", cart.apply_promo("BADCODE"))   # This will crash
