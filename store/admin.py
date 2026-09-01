from django.contrib import admin
from django.shortcuts import redirect
from django.contrib import messages
from datetime import datetime
from.models import Category, Product, Order, ContactMessage, OrderItem, User, ReturnRequest, Review

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone','address', 'created_at')
    search_fields = ('name', 'email','phone')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'size', 'quantity', 'price')
    readonly_fields = ('price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ('transaction_id','name','phone','pincode','total_amount','payment_method','payment_status','shipped_at','delivered_at','created_at')
    list_filter = ('payment_status','payment_method')
    search_fields = ('transaction_id','name','phone','pincode')
    actions = ['mark_delivered', 'mark_pending', 'mark_shipped']

    @admin.action(description='✅ Delivered')
    def mark_delivered(self, request, queryset):
        for o in queryset:
            Order.objects.filter(transaction_id=o.transaction_id).update(payment_status='Delivered', delivered_at=datetime.now())
        self.message_user(request, f"✅ Delivered!")

    @admin.action(description='⌛ Pending')
    def mark_pending(self, request, queryset):
        for o in queryset:
            Order.objects.filter(transaction_id=o.transaction_id).update(payment_status='pending', delivered_at=None, shipped_at=None)
        self.message_user(request, "Pending!")

    @admin.action(description='🚚 Shipped')
    def mark_shipped(self, request, queryset):
        for o in queryset:
            Order.objects.filter(transaction_id=o.transaction_id).update(payment_status='Shipped', shipped_at=datetime.now(), delivered_at=None)
        self.message_user(request, "Shipped!")

    def changelist_view(self, request, extra_context=None):
        if request.GET.get('old') == '1':
            q = request.GET.copy()
            q.pop('old', None)
            request.GET = q
            self.change_list_template = "admin/change_list.html"
            return super().changelist_view(request, extra_context)

        self.change_list_template = "admin/order_grouped.html"
        if request.method == 'POST' and 'txn_id' in request.POST:
            txn_id = request.POST.get('txn_id')
            new_status = request.POST.get('new_status')
            shipped_at_str = request.POST.get('shipped_at')
            delivered_at_str = request.POST.get('delivered_at')

            if txn_id and new_status:
                update_data = {'payment_status': new_status}

                if new_status == 'Shipped':
                    if shipped_at_str:
                        try:
                            dt = datetime.fromisoformat(shipped_at_str)
                            update_data['shipped_at'] = dt
                        except:
                            update_data['shipped_at'] = datetime.now()
                    else:
                        update_data['shipped_at'] = datetime.now()
                    update_data['delivered_at'] = None

                elif new_status == 'Delivered':
                    if delivered_at_str:
                        try:
                            dt = datetime.fromisoformat(delivered_at_str)
                            update_data['delivered_at'] = dt
                        except:
                            update_data['delivered_at'] = datetime.now()
                    else:
                        update_data['delivered_at'] = datetime.now()

                else:
                    update_data['delivered_at'] = None
                    update_data['shipped_at'] = None

                Order.objects.filter(transaction_id=txn_id).update(**update_data)
                messages.success(request, f"Txn {txn_id} -> {new_status}")
                return redirect(request.path)

        all_orders = self.get_queryset(request).select_related('user').order_by('-created_at')
        groups = {}
        for o in all_orders:
            tid = o.transaction_id or f"OLD-{o.id}"
            if tid not in groups:
                groups[tid] = {'orders': [], 'group_total': 0, 'return_request': None}
            groups[tid]['orders'].append(o)
            groups[tid]['group_total'] += o.total_amount

        for txn_id in groups.keys():
            return_req = ReturnRequest.objects.filter(order_group_id=txn_id).first()
            groups[txn_id]['return_request'] = return_req

        extra_context = extra_context or {}
        extra_context['grouped_orders'] = groups
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','name')
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id','name','price','discount_price','stock','category')
    list_editable = ('price','discount_price','stock')
    list_display_links = ('id','name')
    search_fields = ('name','brand')
    list_filter = ('category','brand')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id','name','created_at')
    readonly_fields = ('created_at',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user_id', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['product__name']

@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ['order_group_id', 'reason', 'status']
    list_filter = ['status']
    list_editable = ['status']
    search_fields = ['order_group_id', 'reason']
    actions = ['approve_returns', 'reject_returns']

    @admin.action(description="✅ Approve selected returns")
    def approve_returns(self, request, queryset):
        queryset.update(status='Approved')
        self.message_user(request, f"{queryset.count()} Returns Approved!")

    @admin.action(description="❌ Reject selected returns")
    def reject_returns(self, request, queryset):
        queryset.update(status='Rejected')
        self.message_user(request, f"{queryset.count()} Returns Rejected!")