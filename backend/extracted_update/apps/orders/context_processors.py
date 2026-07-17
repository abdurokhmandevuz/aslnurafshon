def cart_processor(request):
    cart = request.session.get('cart', {})
    return {'cart_count': sum(cart.values())}
