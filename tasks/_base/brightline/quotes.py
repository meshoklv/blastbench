"""Commercial quotes: money formatting, titles and the printable text."""
from brightline.models import Quote


def format_money(cents):
    """Format integer cents as US dollars: 1234567 -> '$12,345.67'."""
    sign = "-" if cents < 0 else ""
    dollars, rest = divmod(abs(cents), 100)
    return f"{sign}${dollars:,}.{rest:02d}"


def pluralize(unit, count):
    """'pallet' x1 -> 'pallet', 'box' x3 -> 'boxes', 'pallet' x2 -> 'pallets'."""
    if count == 1:
        return unit
    if unit.endswith(("s", "x", "ch", "sh")):
        return unit + "es"
    return unit + "s"


def quote_title(quote):
    """Header line of the quote."""
    qty = f"{quote.quantity} {pluralize(quote.unit, quote.quantity)}"
    return (f"Freight quote for {quote.client_name}: {qty} "
            f"from {quote.origin} to {quote.destination}")


def subtotal_cents(quote):
    return sum(cents for _, cents in quote.lines)


def tax_cents(quote):
    """Tax on the subtotal, rounded half up to the cent."""
    return (subtotal_cents(quote) * quote.tax_rate_bp + 5000) // 10000


def total_cents(quote):
    return subtotal_cents(quote) + tax_cents(quote)


def render_quote(quote):
    """Printable plain-text quote."""
    out = [quote_title(quote), "=" * 40]
    for description, cents in quote.lines:
        out.append(f"{description:<28}{format_money(cents):>12}")
    out.append("-" * 40)
    out.append(f"{'Subtotal':<28}{format_money(subtotal_cents(quote)):>12}")
    if quote.tax_rate_bp:
        label = f"Tax ({quote.tax_rate_bp / 100:.2f}%)"
        out.append(f"{label:<28}{format_money(tax_cents(quote)):>12}")
    out.append(f"{'Total':<28}{format_money(total_cents(quote)):>12}")
    return "\n".join(out)
