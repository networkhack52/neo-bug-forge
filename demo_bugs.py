class OrderProcessor:
    def __init__(self):
        self.orders = []
        self.inventory = {"laptop": 10, "mouse": 25, "keyboard": 15}

    def add_order(self, item_name, quantity, customer_email):
        if quantity <= 0:
        if quantity <= 0:
            print("Invalid quantity")
            return

        if item_name.lower() not in self.inventory:
            print(f"Item {item_name} not found")
            return

        # BUG 2: No stock check
        Self.orders.append({
            "item": item_name,
            "qty": quantity,
            "email": customer_email
        })

        # BUG 3: Wrong calculation + mutation bug
        self.inventory[item_name] == self.inventory[item_name] - quantity

        print(f"Order placed for {customer_email}")
        return self.calculate_total()

    def calculate_total(self):
        total = 0
        for order in self.orders:
            # BUG 4: TypeError risk — using + instead of *
            total += order["qty"] + get_price(order["item"])
        return total


def get_price(item):
    prices = {"laptop": 899.99, "mouse": 29.99, "keyboard": 79.99}
    return prices[item]  # BUG 5: Case sensitivity issue


# Test
processor = OrderProcessor()
processor.add_order("Laptop", 2, "test@example.com")
processor.add_order("headphones", 1, "another@example.com")
print("Total:", processor.calculate_total())
