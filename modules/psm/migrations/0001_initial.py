import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ItemMaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('item_code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('category', models.CharField(choices=[('CONSUMABLE', 'Consumable'), ('EQUIPMENT', 'Equipment'), ('SERVICE', 'Service'), ('FURNITURE', 'Furniture')], default='CONSUMABLE', max_length=32)),
                ('unit_of_measure', models.CharField(choices=[('PIECE', 'Piece'), ('BOX', 'Box'), ('KG', 'Kilogram'), ('METER', 'Meter'), ('PACKET', 'Packet'), ('SET', 'Set')], default='PIECE', max_length=32)),
                ('minimum_stock_level', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'psm_item_master',
                'ordering': ['item_code'],
            },
        ),
        migrations.CreateModel(
            name='Indent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_id', models.IntegerField(db_index=True)),
                ('indent_number', models.CharField(max_length=64, unique=True)),
                ('department_code', models.CharField(db_index=True, max_length=64)),
                ('title', models.CharField(max_length=255)),
                ('purpose', models.TextField()),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('NORMAL', 'Normal'), ('HIGH', 'High'), ('EMERGENCY', 'Emergency')], default='NORMAL', max_length=32)),
                ('estimated_total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('PENDING_DEPT_APPROVAL', 'Pending Department Approval'), ('PENDING_PS_REVIEW', 'Pending PS Review'), ('PENDING_DIRECTOR_APPROVAL', 'Pending Director Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled'), ('FULFILLED', 'Fulfilled')], db_index=True, default='DRAFT', max_length=32)),
                ('current_approver_role', models.CharField(blank=True, max_length=64)),
                ('rejection_reason', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'psm_indent',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('estimated_total__gte', 0)), name='psm_indent_estimated_total_non_negative'), models.CheckConstraint(condition=models.Q(('status__in', ['DRAFT', 'SUBMITTED', 'PENDING_DEPT_APPROVAL', 'PENDING_PS_REVIEW', 'PENDING_DIRECTOR_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED', 'FULFILLED'])), name='psm_indent_status_valid')],
            },
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('po_number', models.CharField(max_length=64, unique=True)),
                ('procurement_method', models.CharField(choices=[('DIRECT', 'Direct Procurement'), ('QUOTATION', 'Quotation / Committee'), ('TENDER', 'Open / Limited Tender'), ('GEM', 'Government e-Marketplace (GeM)')], default='DIRECT', max_length=32)),
                ('total_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ISSUED', 'Issued'), ('PARTIALLY_DELIVERED', 'Partially Delivered'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], db_index=True, default='DRAFT', max_length=32)),
                ('delivery_due_date', models.DateField(blank=True, null=True)),
                ('issued_by_user_id', models.IntegerField(blank=True, null=True)),
                ('issued_at', models.DateTimeField(blank=True, null=True)),
                ('indent', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_order', to='psm.indent')),
            ],
            options={
                'db_table': 'psm_purchase_order',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='POLineItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity_ordered', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('item_master', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='po_lines', to='psm.itemmaster')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='psm.purchaseorder')),
            ],
            options={
                'db_table': 'psm_po_line_item',
            },
        ),
        migrations.CreateModel(
            name='GoodsReceiptNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('grn_number', models.CharField(max_length=64, unique=True)),
                ('store_keeper_user_id', models.IntegerField()),
                ('challan_number', models.CharField(blank=True, max_length=128)),
                ('invoice_number', models.CharField(blank=True, max_length=128)),
                ('receipt_date', models.DateField()),
                ('status', models.CharField(choices=[('INSPECTION_PENDING', 'Inspection Pending'), ('ACCEPTED', 'Accepted'), ('DISCREPANT', 'Discrepant'), ('CLOSED', 'Closed')], db_index=True, default='INSPECTION_PENDING', max_length=32)),
                ('indentor_acknowledged', models.BooleanField(default=False)),
                ('indentor_acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='goods_receipts', to='psm.purchaseorder')),
            ],
            options={
                'db_table': 'psm_goods_receipt_note',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StockItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity_on_hand', models.PositiveIntegerField(default=0)),
                ('quantity_reserved', models.PositiveIntegerField(default=0)),
                ('item_master', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stock', to='psm.itemmaster')),
            ],
            options={
                'db_table': 'psm_stock_item',
            },
        ),
        migrations.CreateModel(
            name='StockLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(choices=[('RECEIPT_CREDIT', 'Goods Receipt Credit'), ('INTERNAL_ISSUE', 'Internal Departmental Issue'), ('RESERVATION_LOCK', 'Stock Reservation Lock'), ('RESERVATION_RELEASE', 'Stock Reservation Release'), ('ADJUSTMENT', 'Inventory Audit Adjustment')], max_length=32)),
                ('quantity', models.IntegerField()),
                ('balance_after', models.PositiveIntegerField()),
                ('reference_id', models.CharField(blank=True, max_length=128)),
                ('recorded_by_user_id', models.IntegerField()),
                ('remarks', models.TextField(blank=True)),
                ('stock_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ledger_entries', to='psm.stockitem')),
            ],
            options={
                'db_table': 'psm_stock_ledger',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vendor_code', models.CharField(max_length=64, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('gstin', models.CharField(max_length=15, unique=True)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(max_length=32)),
                ('address', models.TextField(blank=True)),
                ('bank_account_number', models.CharField(blank=True, max_length=64)),
                ('bank_ifsc', models.CharField(blank=True, max_length=32)),
                ('status', models.CharField(choices=[('PENDING_VERIFICATION', 'Pending Verification'), ('VERIFIED', 'Verified'), ('BLACKLISTED', 'Blacklisted'), ('SUSPENDED', 'Suspended')], db_index=True, default='PENDING_VERIFICATION', max_length=32)),
                ('verified_by_user_id', models.IntegerField(blank=True, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'psm_vendor',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('status__in', ['PENDING_VERIFICATION', 'VERIFIED', 'BLACKLISTED', 'SUSPENDED'])), name='psm_vendor_status_valid')],
            },
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='vendor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='purchase_orders', to='psm.vendor'),
        ),
        migrations.CreateModel(
            name='DiscrepancyReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('discrepancy_code', models.CharField(max_length=64, unique=True)),
                ('reported_by_user_id', models.IntegerField()),
                ('discrepancy_type', models.CharField(choices=[('SHORTAGE', 'Shortage'), ('DAMAGED', 'Damaged Items'), ('SPEC_MISMATCH', 'Specification Mismatch'), ('WRONG_ITEM', 'Wrong Item Delivered')], default='DAMAGED', max_length=32)),
                ('details', models.TextField()),
                ('status', models.CharField(choices=[('OPEN_HOLD_PAYMENT', 'Open - Payment on Hold'), ('VENDOR_NOTIFIED', 'Vendor Notified'), ('REPLACED', 'Replaced'), ('CREDIT_NOTE_ISSUED', 'Credit Note Issued'), ('RESOLVED', 'Resolved')], db_index=True, default='OPEN_HOLD_PAYMENT', max_length=32)),
                ('resolution_summary', models.TextField(blank=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('grn', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='discrepancy_report', to='psm.goodsreceiptnote')),
            ],
            options={
                'db_table': 'psm_discrepancy_report',
                'ordering': ['-created_at'],
                'constraints': [models.CheckConstraint(condition=models.Q(('status__in', ['OPEN_HOLD_PAYMENT', 'VENDOR_NOTIFIED', 'REPLACED', 'CREDIT_NOTE_ISSUED', 'RESOLVED'])), name='psm_discrepancy_status_valid')],
            },
        ),
        migrations.CreateModel(
            name='IndentItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity_requested', models.PositiveIntegerField()),
                ('estimated_unit_cost', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('specifications', models.TextField(blank=True)),
                ('indent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='psm.indent')),
                ('item_master', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='indent_items', to='psm.itemmaster')),
            ],
            options={
                'db_table': 'psm_indent_item',
                'constraints': [models.CheckConstraint(condition=models.Q(('quantity_requested__gt', 0)), name='psm_indent_item_qty_positive'), models.CheckConstraint(condition=models.Q(('estimated_unit_cost__gte', 0)), name='psm_indent_item_cost_non_negative')],
            },
        ),
        migrations.CreateModel(
            name='GRNItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity_received', models.PositiveIntegerField()),
                ('quantity_accepted', models.PositiveIntegerField(default=0)),
                ('quantity_rejected', models.PositiveIntegerField(default=0)),
                ('rejection_remarks', models.TextField(blank=True)),
                ('grn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='psm.goodsreceiptnote')),
                ('po_line_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='grn_items', to='psm.polineitem')),
            ],
            options={
                'db_table': 'psm_grn_item',
                'constraints': [models.CheckConstraint(condition=models.Q(('quantity_received__gte', 0)), name='psm_grn_item_received_non_negative'), models.CheckConstraint(condition=models.Q(('quantity_accepted__gte', 0)), name='psm_grn_item_accepted_non_negative'), models.CheckConstraint(condition=models.Q(('quantity_rejected__gte', 0)), name='psm_grn_item_rejected_non_negative')],
            },
        ),
        migrations.AddConstraint(
            model_name='polineitem',
            constraint=models.CheckConstraint(condition=models.Q(('quantity_ordered__gt', 0)), name='psm_po_line_qty_positive'),
        ),
        migrations.AddConstraint(
            model_name='polineitem',
            constraint=models.CheckConstraint(condition=models.Q(('unit_price__gte', 0)), name='psm_po_line_unit_price_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='goodsreceiptnote',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['INSPECTION_PENDING', 'ACCEPTED', 'DISCREPANT', 'CLOSED'])), name='psm_grn_status_valid'),
        ),
        migrations.AddConstraint(
            model_name='stockitem',
            constraint=models.CheckConstraint(condition=models.Q(('quantity_reserved__lte', models.F('quantity_on_hand'))), name='psm_stock_reserved_lte_on_hand'),
        ),
        migrations.AddConstraint(
            model_name='purchaseorder',
            constraint=models.CheckConstraint(condition=models.Q(('total_amount__gte', 0)), name='psm_po_total_non_negative'),
        ),
        migrations.AddConstraint(
            model_name='purchaseorder',
            constraint=models.CheckConstraint(condition=models.Q(('status__in', ['DRAFT', 'ISSUED', 'PARTIALLY_DELIVERED', 'COMPLETED', 'CANCELLED'])), name='psm_po_status_valid'),
        ),
    ]
