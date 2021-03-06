# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2016, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the AGPLv3 license found in the
# LICENSE file in the root directory of this source tree.
import os
import pytest

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from shuup.core.models import (
    Order, OrderStatus, OrderStatusRole, PersonContact, Product
)
from shuup.testing.browser_utils import (
    click_element, wait_until_appeared, wait_until_condition,
    wait_until_disappeared
)
from shuup.testing.factories import (
    create_product, get_default_payment_method, get_default_shipping_method,
    get_default_shop, get_default_supplier
)
from shuup.testing.utils import initialize_front_browser_test

pytestmark = pytest.mark.skipif(os.environ.get("SHUUP_BROWSER_TESTS", "0") != "1", reason="No browser tests run.")


def create_orderable_product(name, sku, price):
    supplier = get_default_supplier()
    shop = get_default_shop()
    product = create_product(sku=sku, shop=shop, supplier=supplier, default_price=price, name=name)
    return product


@override_settings(SHUUP_REGISTRATION_REQUIRES_ACTIVATION=False)
@pytest.mark.urls('shuup.testing.checkout_with_login_and_register_urls')
@pytest.mark.browser
@pytest.mark.djangodb
def test_checkout_with_login_and_register(browser, live_server, settings):
    # initialize
    product_name = "Test Product"
    get_default_shop()
    pm = get_default_payment_method()
    sm = get_default_shipping_method()
    product = create_orderable_product(product_name, "test-123", price=100)
    OrderStatus.objects.create(
        identifier="initial",
        role=OrderStatusRole.INITIAL,
        name="initial",
        default=True
    )

    # Initialize test and go to front page
    browser = initialize_front_browser_test(browser, live_server)

    assert browser.is_text_present("Welcome to Default!")
    navigate_to_checkout(browser, product)

    # Let's assume that after addresses the checkout is normal
    assert browser.is_text_present("Checkout: Choose Checkout Method")
    guest_ordering_test(browser, live_server)

    test_username = "test_username"
    test_email = "test@example.com"
    test_password = "test_password"
    assert browser.is_text_present("Checkout: Choose Checkout Method")
    register_test(browser, live_server, test_username, test_email, test_password)

    assert browser.is_text_present("Checkout: Choose Checkout Method")
    login_and_finish_up_the_checkout(browser, live_server, test_username, test_email, test_password)


@override_settings(SHUUP_REGISTRATION_REQUIRES_ACTIVATION=False)
@pytest.mark.urls('shuup.testing.single_page_checkout_with_login_and_register_conf')
@pytest.mark.browser
@pytest.mark.djangodb
def test_single_page_checkout_with_login_and_register(browser, live_server, settings):
    # initialize
    product_name = "Test Product"
    get_default_shop()
    pm = get_default_payment_method()
    sm = get_default_shipping_method()
    product = create_orderable_product(product_name, "test-123", price=100)
    OrderStatus.objects.create(
        identifier="initial",
        role=OrderStatusRole.INITIAL,
        name="initial",
        default=True
    )

    # Initialize test and go to front page
    browser = initialize_front_browser_test(browser, live_server)

    assert browser.is_text_present("Welcome to Default!")
    navigate_to_checkout(browser, product)

    # Let's assume that after addresses the checkout is normal
    assert browser.is_text_present("Choose Checkout Method")
    test_username = "test_username"
    test_email = "test@example.com"
    test_password = "test_password"
    register_test(browser, live_server, test_username, test_email, test_password)

    login_and_finish_up_the_checkout(browser, live_server, test_username, test_email, test_password)


def navigate_to_checkout(browser, product):
    assert browser.is_text_present("Newest Products")
    assert browser.is_text_present(product.name)

    click_element(browser, "#product-%s" % product.pk)  # open product from product list
    click_element(browser, "#add-to-cart-button-%s" % product.pk)  # add product to basket

    wait_until_appeared(browser, ".cover-wrap")
    wait_until_disappeared(browser, ".cover-wrap")

    click_element(browser, "#navigation-basket-partial")  # open upper basket navigation menu
    click_element(browser, "a[href='/basket/']")  # click the link to basket in dropdown
    assert browser.is_text_present("Shopping cart")  # we are in basket page
    assert browser.is_text_present(product.name)  # product is in basket

    click_element(browser, "a[href='/checkout/']") # click link that leads to checkout


def guest_ordering_test(browser, live_server):
    browser.fill("login-username", "test-username")
    click_element(browser, "button[name='login']")
    wait_until_appeared(browser, "div.form-group.passwordinput.required.has-error")
    browser.fill("login-password", "test-password")
    click_element(browser, "button[name='login']")
    assert browser.is_text_present("Please enter a correct username and password.")
    wait_until_appeared(browser, "div.alert.alert-danger")

    click_element(browser, "button[data-id='id_checkout_method_choice-register']")
    click_element(browser, "li[data-original-index='0'] a")
    click_element(browser, "div.clearfix button.btn.btn-primary.btn-lg.pull-right")
    assert browser.is_text_present("Checkout: Addresses")
    url = reverse("shuup:checkout", kwargs={"phase": "checkout_method"})
    browser.visit("%s%s" % (live_server, url))


def register_test(browser, live_server, test_username, test_email, test_password):
    click_element(browser, "button[data-id='id_checkout_method_choice-register']")
    click_element(browser, "li[data-original-index='1'] a")
    click_element(browser, "div.clearfix button.btn.btn-primary.btn-lg.pull-right")
    wait_until_condition(browser, lambda x: x.is_text_present("Register"))

    browser.find_by_id("id_username").fill(test_username)
    browser.find_by_id("id_email").fill(test_email)
    browser.find_by_id("id_password1").fill(test_password)
    browser.find_by_id("id_password2").fill("typo-%s" % test_password)
    click_element(browser, "div.clearfix button.btn.btn-primary.btn-lg.pull-right")
    wait_until_appeared(browser, "div.form-group.passwordinput.required.has-error")

    browser.find_by_id("id_password1").fill(test_password)
    browser.find_by_id("id_password2").fill(test_password)
    click_element(browser, "div.clearfix button.btn.btn-primary.btn-lg.pull-right")

    wait_until_condition(browser, lambda x: x.is_text_present("Addresses"))
    # Reload here just in case since there might have been reload with JS
    # which might cause issues with tests since the elements is in cache
    browser.reload()

    # Log out and go back to checkout choice phase
    click_element(browser, "div.top-nav i.menu-icon.fa.fa-user")
    click_element(browser, "a[href='/logout/']")

    # Ensure that the language is still english. It seems that the language might change
    # during the logout.
    browser.find_by_id("language-changer").click()
    browser.find_by_xpath('//a[@class="language"]').first.click()

    # There is no products on basket anymore so let's add one
    product = Product.objects.first()
    product_url = reverse("shuup:product", kwargs={"pk": product.pk, "slug": product.slug})
    browser.visit("%s%s" % (live_server, product_url))
    click_element(browser, "#add-to-cart-button-%s" % product.pk)  # add product to basket

    wait_until_appeared(browser, ".cover-wrap")
    wait_until_disappeared(browser, ".cover-wrap")

    browser.visit("%s%s" % (live_server, "/checkout/"))


def login_and_finish_up_the_checkout(browser, live_server, test_username, test_email, test_password):
    browser.fill("login-username", test_email)
    browser.fill("login-password", test_password)
    click_element(browser, "button[name='login']")

    wait_until_condition(browser, lambda x: x.is_text_present("Addresses"), timeout=100)
    # Reload here just in case since there might have been reload with JS
    # which might cause issues with tests since the elements is in cache
    browser.reload()

    # This should be first order upcoming
    assert Order.objects.count() == 0

    # Fnish the checkout
    customer_name = "Test Tester"
    customer_street = "Test Street"
    customer_city = "Test City"
    customer_region = "CA"
    customer_country = "US"

    # Fill all necessary information
    browser.fill("billing-name", customer_name)
    browser.fill("billing-street", customer_street)
    browser.fill("billing-city", customer_city)
    browser.select("billing-country", customer_country)
    wait_until_appeared(browser, "select[name='billing-region_code']")
    browser.select("billing-region_code", customer_region)

    click_element(browser, "#addresses button[type='submit']")

    wait_until_condition(browser, lambda x: x.is_text_present("This field is required."))

    browser.fill("shipping-name", customer_name)
    browser.fill("shipping-street", customer_street)
    browser.fill("shipping-city", customer_city)
    browser.select("shipping-country", customer_country)

    click_element(browser, "#addresses button[type='submit']")
    assert browser.is_text_present("Shipping & Payment")

    pm = get_default_payment_method()
    sm = get_default_shipping_method()

    assert browser.is_text_present(sm.name)  # shipping method name is present
    assert browser.is_text_present(pm.name)  # payment method name is present

    click_element(browser, ".btn.btn-primary.btn-lg.pull-right")  # click "continue" on methods page

    assert browser.is_text_present("Confirmation")  # we are indeed in confirmation page
    product = Product.objects.first()

    # See that all expected texts are present
    assert browser.is_text_present(product.name)
    assert browser.is_text_present(sm.name)
    assert browser.is_text_present(pm.name)
    assert browser.is_text_present("Delivery")
    assert browser.is_text_present("Billing")

    # check that user information is available
    assert browser.is_text_present(customer_name)
    assert browser.is_text_present(customer_street)
    assert browser.is_text_present(customer_city)
    assert browser.is_text_present("United States")

    browser.execute_script('document.getElementById("id_accept_terms").checked=true')  # click accept terms
    click_element(browser, ".btn.btn-primary.btn-lg")  # click "place order"

    assert browser.is_text_present("Thank you for your order!")  # order succeeded

    # Let's make sure the order now has a customer
    assert Order.objects.count() == 1
    order = Order.objects.first()
    assert order.customer == PersonContact.objects.filter(user__username=test_username).first()
    assert order.customer.name == customer_name
    assert order.customer.default_shipping_address is not None
    assert order.customer.default_billing_address is not None
    assert order.customer.user.username == test_username
