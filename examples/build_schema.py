#!/usr/bin/env python3
"""A full schema, built two ways: DSL text and the Python builder.

Combines a named type, an enum, a required array with a minimum length, an
optional field, and a map (the "rest" of an object) -- the pieces most
schemas actually need together, not in isolation. See docs/schema.md for the
full write-up this example backs.

Run: python3 examples/build_schema.py
"""
from dataspec import arr, doc, enum, mapping, obj, optional, parse_schema, schema, t

DSL = """
type Address = { street: string, city: string }
type LineItem = { sku: string, qty: integer, price: number }

root {
    order: {
        id:      string,
        status:  "pending" | "shipped" | "cancelled",
        total:   number,
        address: Address,
        items:   [LineItem]+,          # at least one line item
        coupon?: string,               # optional
        tags:    { [string]: string }, # arbitrary extra keys -> string
    },
}
"""


def builder_schema():
    address_t = obj(street=t.string, city=t.string)
    line_item_t = obj(sku=t.string, qty=t.integer, price=t.number)
    order_t = obj(
        id=t.string,
        status=enum("pending", "shipped", "cancelled"),
        total=t.number,
        address=address_t,
        items=arr(line_item_t, min=1),
        coupon=optional(t.string),
        tags=mapping(t.string),
    )
    return schema(obj(order=order_t))


def main():
    s_dsl = parse_schema(DSL)
    s_builder = builder_schema()

    print("== the builder produces the same schema as the DSL text ==")
    print("equivalent:", s_dsl.equivalent(s_builder))

    good = {
        "order": {
            "id": "A1001",
            "status": "shipped",
            "total": 29.97,
            "address": {"street": "1 Main St", "city": "London"},
            "items": [{"sku": "WIDGET", "qty": 3, "price": 9.99}],
            "tags": {"region": "EU"},
        }
    }
    print("\n== a valid document (coupon omitted -- it's optional) ==")
    print(s_dsl.validate(doc(good)))

    bad = {
        "order": {
            "id": "A1002",
            "status": "lost",          # not one of the enum values
            "total": 10,
            "address": {"street": "2 Main St", "city": "London"},
            "items": [],                # violates the [LineItem]+ minimum
            "tags": {},
        }
    }
    print("\n== an invalid document -- every problem, with its exact path ==")
    print(s_dsl.validate(doc(bad)))

    print("\n== navigate the schema with uniform getters ==")
    order_type = s_dsl.root.field("order")
    print("order's fields:", [name for name, _ in order_type.children()])


if __name__ == "__main__":
    main()
