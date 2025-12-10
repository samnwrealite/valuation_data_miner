Core Tables for Property Management Analytics
Based on the schema, here are the key table groups:
### 1. Property & Unit Management

properties: Core property information

id, property_code, name, merchant_id, location, status, type, category, landlord_id, manager_id, region_id


units: Individual rental units

id, name, property_id, rent, service_charge, deposit, status, category, space, floor_id, leased


floors: Building floors

id, property_id, name, type, space



2. Tenant & Lease Management

tenants: Tenant records

id, tenant_code, name, user_id, property_id, start_date, end_date, status, billing_cycle, billing_period, next_due, terminated_at


lease_items: Items leased to tenants

id, tenant_id, item_id, item_type, category, rent, service_charge, amount, status


users: Tenant user details

id, first_name, last_name, email, phone, status, type



3. Financial - Revenue

invoices: Billing to tenants

id, invoice_no, tenant_id, property_id (via item_id/item_type), amount, vat, total, paid, balance, due_date, status, period


invoice_items: Invoice line items

id, invoice_id, notes, type, quantity, cost, amount, vat, total, paid, period


payments: Payment receipts

id, tenant_id, property_id, amount, total, payment_date, status, mode, channel


invoice_payments: Payment allocations

id, invoice_id, amount, trx_no



4. Financial - Expenses

bills: Supplier/contractor bills

id, contract_id, bill_no, amount, vat, total, paid, balance, due_date, status, category


bill_items: Bill line items

id, bill_id, expense_id, amount, quantity, cost, vat, total


contracts: Supplier contracts

id, contractor_id, property_id, administrative_expense_id, amount, cyclic, billing_cycle, status



5. Utilities

utility_billings: Water/electricity billing

id, property_id, tenant_id, type, period, consumption, amount, vat, total



6. Accounting

ledgers: General ledger entries

id, account_id, notes, credit, debit, balance, txn_date, type, ref


accounts: Chart of accounts

id, name, code, account_type_id, balance, status, category


remittances: Landlord remittances

id, merchant_id, property_id, period_from, period_to, collected, expenses, amount, status



### 7. Master Data

merchants: Landlords/property owners

id, name, email, phone, type, status


bank_accounts: Bank account details

id, owner_id, name, account_no, bank_id, type


administrative_expenses: Expense categories

id, name, expense_code, category



### 8. Operational

tickets: Maintenance tickets

id, ticket_no, property_id, tenant_id, category_id, priority, status, created_at, date_closed


tasks: Task management

id, title, property_id, tenant_id, status, priority, due_date