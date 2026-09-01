from django.shortcuts import render, redirect, get_object_or_404
from.models import Product, Category, User, Order, OrderItem, ContactMessage, Review, Wishlist, ReturnRequest
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages
import uuid, json
from django.utils import timezone
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

def home(request):
    products = Product.objects.all().order_by('-created_at')[:9]
    featured_names = ["White Elegant Organza", "Red Long Party Wear Gown", "Modern Purple Banarasi", "Blue Check Formal Blazer"]
    featured_products = []
    for name_part in featured_names:
        p = Product.objects.filter(name__icontains=name_part).first()
        if p: featured_products.append(p)
    if len(featured_products) < 4:
        extra = Product.objects.exclude(id__in=[x.id for x in featured_products]).order_by('-created_at')[:4-len(featured_products)]
        featured_products.extend(list(extra))
    return render(request, 'index.html', {'products': products, 'featured_products': featured_products})

def shop(request):
    best_order = ["White Elegant Organza", "Red Long Party", "Modern Purple", "Blue Check"]
    products = Product.objects.all().order_by('-created_at')
    top = []
    rest = list(products)
    for name in best_order:
        for p in rest:
            if name.lower() in p.name.lower():
                top.append(p)
                rest.remove(p)
                break
    products = top + rest
    categories = Category.objects.all()
    return render(request, 'shop.html', {'products': products, 'categories': categories})

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    related = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    avg = reviews.aggregate(Avg('rating'))['rating__avg']
    return render(request, 'product.html', {
        'product': product, 
        'related': related,
        'reviews': reviews,
        'avg_rating': round(avg, 1) if avg else 0,
        'review_count': reviews.count()
    })
def cart(request):
    products = Product.objects.all()
    prod_dict = {}
    for p in products:
        img_url = str(p.image) if p.image else ""
        prod_dict[str(p.id)] = {"name": p.name, "price": str(p.final_price), "original_price": str(p.price), "discount_percent": p.discount_percent, "img": img_url}
    return render(request, 'cart.html', {'products_json': json.dumps(prod_dict)})

def checkout(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        pincode = request.POST.get('pincode')
        payment_method = request.POST.get('payment_method', 'COD')
        payment_status = 'pending' if payment_method == 'COD' else 'paid'
        txn = f"COD-{uuid.uuid4().hex[:8].upper()}"
        cart_json = request.POST.get('cart_json', '')
        try:
            cart_items = json.loads(cart_json) if cart_json else []
        except:
            cart_items = []
        if not cart_items:
            messages.error(request, "Cart empty!")
            return redirect('/cart/')

        total_qty = 0
        total_paid = 0
        temp_orders_data = []
        for item in cart_items:
            prod_id = item.get('id') or item.get('product_id')
            qty = int(item.get('quantity') or item.get('qty') or 1)
            size = item.get('size', 'M')
            product = Product.objects.filter(id=prod_id).first()
            if not product: continue
            cart_price = int(float(item.get('price') or product.final_price))
            total_qty += qty
            total_paid += cart_price * qty
            temp_orders_data.append((product, qty, size, cart_price))

        if not temp_orders_data: return redirect('/cart/')

        master_order = Order.objects.create(
            quantity=total_qty, size='Mixed', name=name, phone=phone,
            address=address, pincode=pincode, payment_method=payment_method,
            payment_status=payment_status, transaction_id=txn, total_amount=total_paid
        )
        for product, qty, size, cart_price in temp_orders_data:
            OrderItem.objects.create(order=master_order, product=product, quantity=qty, size=size, price=cart_price)

        return redirect(f"/order_success/?txn={txn}")
    return render(request, 'checkout.html')


def order_success(request):
    txn = request.GET.get('txn')
    order = Order.objects.filter(transaction_id=txn).prefetch_related('items__product').first()
    if not order:
        return redirect('/shop/')

    items_qs = order.items.all()
    total_qty = order.quantity
    total_paid = order.total_amount

    ordered_list = []
    for it in items_qs:
        if hasattr(it, 'product') and it.product:
            ordered_list.append({"id": str(it.product.id), "size": str(it.size)})

    return render(request, 'order_success.html', {
        'first_order': order,
        'orders': items_qs,
        'total_qty': total_qty,
        'total_paid': total_paid,
        'txn_id': txn,
        'ordered_ids': json.dumps(ordered_list)
    })


def orders(request):

    all_orders = Order.objects.all().order_by('-created_at').prefetch_related('items__product')
    grouped_dict = {}

    for o in all_orders:
        txn = o.transaction_id or f"ORD-{o.id}"
        if txn not in grouped_dict:
            grouped_dict[txn] = {'txn_id': txn, 'first_order': o, 'items': [], 'total': 0, 'total_qty': 0, 'return_request': None, 'return_status': None}

        if hasattr(o, 'items') and o.items.exists():
            items = list(o.items.all())
            grouped_dict[txn]['items'] = items
            grouped_dict[txn]['total'] = sum(i.price * i.quantity for i in items)
            grouped_dict[txn]['total_qty'] = sum(i.quantity for i in items)
        else:
            if o not in grouped_dict[txn]['items']:
                grouped_dict[txn]['items'].append(o)
                grouped_dict[txn]['total'] += getattr(o, 'total_amount', 0) or 0
                grouped_dict[txn]['total_qty'] += getattr(o, 'quantity', 0) or 1

    all_return_requests = {r.order_group_id: r for r in ReturnRequest.objects.all()}

    for txn_id, data in grouped_dict.items():
        if txn_id in all_return_requests:
            data['return_request'] = all_return_requests[txn_id]
            data['return_status'] = all_return_requests[txn_id].status

    grouped_list = sorted(grouped_dict.values(), key=lambda x: x['first_order'].created_at, reverse=True)

    customer_id = request.session.get('customer_id')
    reviewed_ids = []
    if customer_id:
        reviewed_ids = list(Review.objects.filter(user_id=customer_id).values_list('product_id', flat=True))

    returned_ids = list(ReturnRequest.objects.values_list('order_group_id', flat=True))

    return render(request, 'my_orders.html', {
        'grouped': grouped_list,
        'reviewed_ids': reviewed_ids,
        'returned_ids': returned_ids
    })

def request_return(request, order_id):
    order = Order.objects.filter(id=order_id).first()
    if order:
        txn = order.transaction_id or f"ORD-{order.id}"
        ReturnRequest.objects.get_or_create(
            order_group_id=txn,
            defaults={'reason': 'Size issue', 'status': 'Requested'}
        )
    return redirect('/my-orders/')



def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                request.session['customer_id'] = user.id
                request.session['customer_name'] = user.name
                return redirect('/')
            else:
                return render(request, 'login.html', {'error': 'Wrong password!'})
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'Email not found!'})
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already exists!'})
        User.objects.create(name=name, email=email, password=make_password(password))
        return redirect('login')
    return render(request, 'register.html')

def about(request): return render(request, 'about.html')
def contact(request):
    if request.method == 'POST':
        ContactMessage.objects.create(name=request.POST.get('name'), mail=request.POST.get('email'), message=request.POST.get('message'))
        messages.success(request, "Message Sent Successfully!")
        return redirect('contact')
    return render(request, 'contact.html')



def get_current_user_id(request):
    if request.user.is_authenticated:
        return request.user.id
    return request.session.get('customer_id')

def wishlist(request):
    uid = get_current_user_id(request)
    if not uid:
        return redirect('login')
    items = Wishlist.objects.filter(user_id=uid).select_related('product')
    if not items.exists():
        items = Wishlist.objects.filter(user__id=uid).select_related('product')
    return render(request, 'wishlist.html', {'items': items})

def wishlist_toggle(request, product_id):
    uid = get_current_user_id(request)
    if not uid:
        return JsonResponse({'status':'login_required'}, status=401)
    try:
        product = Product.objects.get(id=product_id)
        from .models import User as CustomUser
        user_obj = None
        try:
            user_obj = CustomUser.objects.get(id=uid)
        except:
            from django.contrib.auth.models import User as AuthUser
            try:
                user_obj = AuthUser.objects.get(id=uid)
            except:
                pass
        
        wish = Wishlist.objects.filter(user_id=uid, product_id=product_id).first()
        if wish:
            wish.delete()
            return JsonResponse({'status':'removed'})
        else:
            Wishlist.objects.create(user_id=uid, product_id=product_id)
            return JsonResponse({'status':'added'})
    except Exception as e:
        return JsonResponse({'status':'error', 'msg': str(e)}, status=500)

@login_required
def add_to_wishlist(request, id):
    uid = get_current_user_id(request)
    Wishlist.objects.get_or_create(user_id=uid, product_id=id)
    return redirect('wishlist')

@login_required
def remove_from_wishlist(request, id):
    uid = get_current_user_id(request)
    Wishlist.objects.filter(user_id=uid, product_id=id).delete()
    return redirect('wishlist')

def logout_view(request):
    request.session.flush()
    return redirect('home')


def download_invoice(request, txn_id):
    orders = Order.objects.filter(transaction_id=txn_id)
    if not orders.exists():
        return HttpResponse("Order not found!", status=404)
    if not request.user.is_superuser:
        orders = orders.filter(user__username=str(request.user))
        if not orders.exists():
            return HttpResponse("Not allowed!", status=403)

    first_order = orders.first()
    items = OrderItem.objects.filter(order__in=orders)
    total = first_order.total_amount or sum(i.price * i.quantity for i in items)


    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="VASTRA_Invoice_{txn_id}.pdf"'
    
    c = canvas.Canvas(response, pagesize=A4)
    w, h = A4

    BLACK = HexColor("#111111")
    GRAY = HexColor("#6B7280")
    LIGHT_GRAY = HexColor("#F3F4F6")
    ORANGE = HexColor("#FF3F6C")

    c.setFillColor(BLACK)
    c.rect(0, h-70, w, 70, fill=1, stroke=0)
    
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, h-45, "VASTRA")
    c.setFont("Helvetica", 9)
    c.drawString(40, h-60, "Fashion That Defines You | www.vastra.com")

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(w-40, h-45, "TAX INVOICE")

    y = h-100
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Invoice Details:")
    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY)
    c.drawString(40, y-15, f"Invoice No: {txn_id}")
    c.drawString(40, y-28, f"Date: {first_order.created_at.strftime('%d %B %Y, %I:%M %p')}")
    c.drawString(40, y-41, f"Payment: Cash On Delivery")
    c.drawString(40, y-54, f"Order Status: Delivered")

    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, y, "Billed To:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(BLACK)
    c.drawString(320, y-15, f"{first_order.name}")
    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY)
    c.drawString(320, y-28, f"{first_order.phone}")
    addr = f"{first_order.address}, {first_order.pincode}"
    c.drawString(320, y-41, addr[:45])
    if len(addr) > 45:
        c.drawString(320, y-54, addr[45:90])

    y -= 80
    c.setFillColor(LIGHT_GRAY)
    c.rect(40, y-30, w-80, 30, fill=1, stroke=0)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(50, y-12, "Sold By: VASTRA Fashions Pvt Ltd, Tirupati, AP - 517501 | GSTIN: 37ABCDE1234F1Z5 | support@vastra.com")

    y -= 60
    c.setFillColor(BLACK)
    c.rect(40, y, w-80, 25, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y+9, "PRODUCT DETAILS")
    c.drawString(300, y+9, "SIZE")
    c.drawString(340, y+9, "QTY")
    c.drawString(380, y+9, "RATE")
    c.drawString(470, y+9, "AMOUNT")

    y -= 20
    c.setFont("Helvetica", 9)
    for item in items:
        if y < 120:
            c.showPage()
            y = h-80
        
        if items.filter(id=item.id).first() == item: 
            pass
        if y % 40 == 0:
            c.setFillColor(HexColor("#FAFAFA"))
            c.rect(40, y-5, w-80, 20, fill=1, stroke=0)

        c.setFillColor(BLACK)
        prod_name = item.product.name if item.product else "Product"
        c.drawString(50, y, prod_name[:42])
        c.setFillColor(GRAY)
        c.drawString(300, y, str(item.size))
        c.drawString(340, y, str(item.quantity))
        c.drawString(380, y, f"Rs.{item.price}")
        c.setFillColor(BLACK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(470, y, f"Rs.{item.price * item.quantity}")
        c.setFont("Helvetica", 9)
        y -= 22
        c.setStrokeColor(HexColor("#E5E7EB"))
        c.line(40, y+5, w-40, y+5)

    y -= 30
    c.setStrokeColor(BLACK)
    c.line(350, y+15, w-40, y+15)
    c.setFont("Helvetica", 10)
    c.setFillColor(GRAY)
    c.drawString(380, y, "Subtotal:")
    c.setFillColor(BLACK)
    c.drawRightString(w-40, y, f"Rs. {total}")

    y -= 20
    c.setFillColor(GRAY)
    c.drawString(380, y, "Shipping:")
    c.setFillColor(HexColor("#10B981"))
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(w-40, y, "FREE")

    y -= 25
    c.setFillColor(BLACK)
    c.rect(350, y-5, w-390, 28, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(360, y+5, "TOTAL PAID")
    c.drawRightString(w-45, y+5, f"Rs. {total}")

    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(40, 80, "This is a computer generated invoice. No signature required.")
    c.drawString(40, 70, "Return Policy: 7 Days Easy Return")
    
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ORANGE)
    c.drawCentredString(w/2, 50, "Thank You For Shopping With VASTRA! ❤️")

    c.showPage()
    c.save()
    return response


def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        Review.objects.create(
            product=product,
            user_id=request.user.id,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Thank you for your review!")
        return redirect('my_orders')
    return render(request, 'add_review.html', {'product': product})



def profile_view(request):
    if 'customer_id' not in request.session:
        return redirect('login')
    
    from .models import User
    customer = User.objects.get(id=request.session['customer_id'])
    msg = ""

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            customer.name = request.POST.get('name')
            customer.email = request.POST.get('email')
            customer.phone = request.POST.get('phone')
            customer.address = request.POST.get('address')
            customer.save()
            request.session['customer_name'] = customer.name
            msg = "Profile Updated Successfully! ✅"

        elif 'update_password' in request.POST:
            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')
            
            if new_pass == confirm_pass and len(new_pass) >= 4:
                customer.password = new_pass 
                customer.save()
                msg = "Password Changed Successfully! 🔒"
            else:
                msg = "Password mismatch! ❌"

    return render(request, 'profile.html', {'customer': customer, 'msg': msg})