# -*- coding: utf-8 -*-
"""
    checkout.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import json

from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.modules.nereid_checkout.checkout import not_empty_cart, \
sale_has_non_guest_party
from nereid import route, redirect, url_for, render_template, request, flash


__metaclass__ = PoolMeta
__all__ = ['Checkout']


class Checkout:
    __name__ = 'nereid.checkout'


@classmethod
@route('/checkout/delivery-method', methods=['GET', 'POST'])
@not_empty_cart
@sale_has_non_guest_party
def delivery_method(cls):
    '''
    Selection of delivery method (options)
    Based on the shipping address selected, the delivery options
    could be shown to the user. This may include choosing shipping speed
    and if there are multiple items, the option to choose items as they are
    available or all at once.
    '''
    NereidCart = Pool().get('nereid.cart')
    Carrier = Pool().get('carrier')
    Sale = Pool().get('sale.sale')

    cart_sale = NereidCart.open_cart().sale

    if not cart_sale.shipment_address:
        return redirect(url_for('nereid.checkout.shipping_address'))

    if not cart_sale.package_weight:
        # No weight, no shipping. Have fun
        return redirect(url_for('nereid.checkout.payment_method'))

    if request.method == 'POST' and request.form.get('carrier_json'):
        carrier_json = json.loads(request.form.get('carrier_json'))
        Sale.write([cart_sale], {
            'carrier': carrier_json.get('carrier'),
            'ups_service_type': carrier_json.get('ups_service_type'),
            'endicia_mailclass': carrier_json.get('endicia_mailclass'),
        })
        cart_sale.apply_shipping()
        return redirect(url_for('nereid.checkout.payment_method'))

    shipping_overweight = False
    delivery_rates = []
    with Transaction().set_context(sale=cart_sale.id):
        try:
            delivery_rates = [] if cart_sale.require_custom_shipping_quote \
                else Carrier.get_rate_list()
        except UserError, e:
            if '[407] Weight' in e.message:
                # Endicia error code: 407
                # XXX: An ugly way to do this.
                # No separate error code from endicia server.
                shipping_overweight = True
            elif 'WeightExceed: ' in e.message:
                # UPS weight exceed error code
                shipping_overweight = True
            else:
                # Error in fetching rates even after silent flag, will
                # only come when address is invalid
                flash(e.message)
                return redirect(url_for('nereid.checkout.shipping_address'))

    return render_template(
        'checkout/delivery_method.jinja', delivery_rates=delivery_rates,
        sale=cart_sale, shipping_overweight=shipping_overweight
)
